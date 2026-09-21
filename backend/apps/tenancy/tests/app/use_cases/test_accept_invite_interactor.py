from datetime import datetime, timedelta, timezone

import pytest

from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand
from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor
from tenancy.domain.entities.invite import Invite
from tenancy.domain.entities.member import Member
from tenancy.domain.entities.shop import Shop
from tenancy.domain.errors import (
    AlreadyMemberError,
    InviteExhaustedError,
    InviteExpiredError,
    InviteInvalidError,
    ShopClosedError,
    TooManyAttemptsError,
)
from tenancy.domain.services.invite_code import hash_invite_code
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


class _StubInvites:
    def __init__(self, invite, calls=None):
        self.invite = invite
        self.calls = calls if calls is not None else []
        self.lookups = []
        self.used = []

    async def find_shop_id_by_code_hash(self, code_hash):
        self.calls.append("find_shop_id")
        self.lookups.append(code_hash)
        return self.invite.shop_id if self.invite else None

    async def find_by_code_hash_for_update(self, code_hash):
        self.calls.append("find_for_update")
        return self.invite

    async def mark_used(self, invite_id):
        self.used.append(invite_id)


class _StubMembers:
    def __init__(self, already_member=False, calls=None):
        self.already_member = already_member
        self.calls = calls if calls is not None else []
        self.locked = []
        self.added = []

    async def lock_membership_changes(self, shop_id):
        self.calls.append("lock")
        self.locked.append(shop_id)

    async def add(self, shop_id, user_id, role):
        if self.already_member:
            raise AlreadyMemberError("이미 이 매장의 멤버입니다.")
        self.added.append((shop_id, user_id, role))
        return Member(id=21, shop_id=shop_id, user_id=user_id, role=role, joined_at=NOW)


class _StubShops:
    def __init__(self, closed=False):
        self.closed = closed

    async def get_by_id(self, shop_id):
        return Shop(id=shop_id, name="Hiss Haus", business_type="pet_grooming", phone=None,
                    address=None, timezone="Asia/Seoul", suspended_at=None,
                    closed_at=NOW if self.closed else None)


class _StubLimiter:
    def __init__(self, count=1):
        self.count = count

    async def hit(self, user_id):
        return self.count


def _invite(**overrides):
    base = dict(id=9, shop_id=3, role=RoleCode.OWNER, expires_at=NOW + timedelta(days=7),
                max_uses=1, used_count=0, revoked_at=None)
    return Invite(**{**base, **overrides})


def _interactor(invites, members=None, shops=None, limiter=None):
    return AcceptInviteInteractor(
        invites=invites, members=members or _StubMembers(), shops=shops or _StubShops(),
        limiter=limiter or _StubLimiter(), now=lambda: NOW,
    )


async def test_코드가_맞으면_초대의_역할로_합류하고_초대를_쓴_것으로_표시한다():
    invites, members = _StubInvites(_invite()), _StubMembers()
    result = await _interactor(invites, members).accept(AcceptInviteCommand(user_id=5, code="ABCD2345"))
    assert members.added == [(3, 5, RoleCode.OWNER)]
    assert invites.used == [9]
    assert (result.shop_id, result.shop_name, result.role, result.member_id) == (3, "Hiss Haus", "owner", 21)


async def test_입력한_모양이_달라도_같은_해시로_찾는다():
    invites = _StubInvites(_invite())
    await _interactor(invites).accept(AcceptInviteCommand(user_id=5, code=" abcd-2345 "))
    assert invites.lookups == [hash_invite_code("ABCD2345")]


async def test_분당_다섯_번을_넘으면_코드를_찾아보지도_않는다():
    invites = _StubInvites(_invite())
    with pytest.raises(TooManyAttemptsError):
        await _interactor(invites, limiter=_StubLimiter(count=6)).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )
    assert invites.lookups == []


async def test_다섯_번째_시도까지는_받는다():
    invites = _StubInvites(_invite())
    await _interactor(invites, limiter=_StubLimiter(count=5)).accept(
        AcceptInviteCommand(user_id=5, code="ABCD2345")
    )
    assert invites.used == [9]


async def test_모르는_코드는_INVITE_INVALID_다():
    with pytest.raises(InviteInvalidError):
        await _interactor(_StubInvites(None)).accept(AcceptInviteCommand(user_id=5, code="ZZZZ9999"))


async def test_만료된_코드는_INVITE_EXPIRED_다():
    invites, members = _StubInvites(_invite(expires_at=NOW)), _StubMembers()
    with pytest.raises(InviteExpiredError):
        await _interactor(invites, members).accept(AcceptInviteCommand(user_id=5, code="ABCD2345"))
    assert members.added == []


async def test_이미_쓴_코드는_INVITE_EXHAUSTED_다():
    with pytest.raises(InviteExhaustedError):
        await _interactor(_StubInvites(_invite(used_count=1))).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )


async def test_닫힌_매장에는_합류할_수_없다():
    invites, members = _StubInvites(_invite()), _StubMembers()
    with pytest.raises(ShopClosedError):
        await _interactor(invites, members, shops=_StubShops(closed=True)).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )
    assert members.added == [] and invites.used == []


async def test_이미_멤버면_초대를_쓰지_않는다():
    invites = _StubInvites(_invite())
    with pytest.raises(AlreadyMemberError):
        await _interactor(invites, _StubMembers(already_member=True)).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )
    assert invites.used == []


async def test_초대_행을_잠그기_전에_매장_행을_먼저_잠근다():
    """E1 — 내보내기·강등·탈퇴와 같은 순서(매장 → 멤버 → 초대)로 잠가야 교착하지 않는다."""
    calls = []
    invites, members = _StubInvites(_invite(), calls), _StubMembers(calls=calls)
    await _interactor(invites, members).accept(AcceptInviteCommand(user_id=5, code="ABCD2345"))
    assert calls == ["find_shop_id", "lock", "find_for_update"]
    assert members.locked == [3]


async def test_모르는_코드면_아무것도_잠그지_않는다():
    calls = []
    invites, members = _StubInvites(None, calls), _StubMembers(calls=calls)
    with pytest.raises(InviteInvalidError):
        await _interactor(invites, members).accept(AcceptInviteCommand(user_id=5, code="ZZZZ9999"))
    assert calls == ["find_shop_id"]
