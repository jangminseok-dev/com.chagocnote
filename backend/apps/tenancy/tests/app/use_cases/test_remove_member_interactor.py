from datetime import datetime, timezone

import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand
from tenancy.app.use_cases.remove_member_interactor import RemoveMemberInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.errors import LastOwnerError, MemberNotFoundError, NotAMemberError
from tenancy.domain.value_objects.role_code import RoleCode

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"member:manage"}))
# 잠근 뒤 다시 읽는 행위자 — 요청 가드가 본 그대로다.
ACTOR = Member(id=11, shop_id=3, user_id=1, role=RoleCode.OWNER, joined_at=JOINED)


class _StubMembers:
    def __init__(self, target, owner_count=1, actor=ACTOR):
        self.target = target
        self.actor = actor
        self.owner_count = owner_count
        self.removed = []
        self.calls = []
        self.read_member_ids = []

    async def lock_membership_changes(self, shop_id):
        self.calls.append("lock_membership_changes")
        self.locked_shop_id = shop_id

    async def get_active(self, ctx, member_id):
        self.calls.append("get_active")
        self.read_member_ids.append(member_id)
        return self.actor if member_id == ctx.member_id else self.target

    async def count_owners(self, ctx):
        return self.owner_count

    async def remove(self, ctx, member_id):
        self.removed.append((ctx, member_id))


class _StubInvites:
    def __init__(self):
        self.revoked = []

    async def revoke_created_by(self, ctx, member_id):
        self.revoked.append((ctx, member_id))


def _member(role):
    return Member(id=12, shop_id=3, user_id=2, role=role, joined_at=JOINED)


async def test_직원을_내보내고_그가_만든_초대를_무효화한다():
    members, invites = _StubMembers(_member(RoleCode.STAFF)), _StubInvites()
    await RemoveMemberInteractor(members, invites).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.removed == [(CTX, 12)]
    assert invites.revoked == [(CTX, 12)]


async def test_대상을_읽기_전에_매장_행을_잠근다():
    members, invites = _StubMembers(_member(RoleCode.STAFF)), _StubInvites()
    await RemoveMemberInteractor(members, invites).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.calls[:2] == ["lock_membership_changes", "get_active"]
    assert members.locked_shop_id == 3


async def test_없는_멤버여도_매장_행은_먼저_잠근다():
    members = _StubMembers(None)
    with pytest.raises(MemberNotFoundError):
        await RemoveMemberInteractor(members, _StubInvites()).remove(
            RemoveMemberCommand(ctx=CTX, member_id=99)
        )
    assert members.calls == ["lock_membership_changes", "get_active", "get_active"]


async def test_잠근_뒤에_행위자를_먼저_다시_읽는다():
    """F-I2 — 권한 확인과 행위 사이의 틈. 행위자를 대상보다 먼저 다시 읽는다."""
    members, invites = _StubMembers(_member(RoleCode.STAFF)), _StubInvites()
    await RemoveMemberInteractor(members, invites).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.read_member_ids == [11, 12]


async def test_잠근_뒤에_소속이_끊긴_행위자는_아무것도_바꾸지_못한다():
    members, invites = _StubMembers(_member(RoleCode.STAFF), actor=None), _StubInvites()
    with pytest.raises(NotAMemberError):
        await RemoveMemberInteractor(members, invites).remove(
            RemoveMemberCommand(ctx=CTX, member_id=12)
        )
    assert members.removed == []
    assert invites.revoked == []


async def test_잠근_뒤에_역할이_낮춰진_행위자는_아무것도_바꾸지_못한다():
    actor = Member(id=11, shop_id=3, user_id=1, role=RoleCode.STAFF, joined_at=JOINED)
    members, invites = _StubMembers(_member(RoleCode.STAFF), actor=actor), _StubInvites()
    with pytest.raises(NotAMemberError):
        await RemoveMemberInteractor(members, invites).remove(
            RemoveMemberCommand(ctx=CTX, member_id=12)
        )
    assert members.removed == []
    assert invites.revoked == []


async def test_사장이_둘이면_한_명을_내보낼_수_있다():
    members, invites = _StubMembers(_member(RoleCode.OWNER), owner_count=2), _StubInvites()
    await RemoveMemberInteractor(members, invites).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.removed == [(CTX, 12)]
    assert invites.revoked == [(CTX, 12)]


async def test_마지막_사장은_내보낼_수_없고_초대도_그대로다():
    members, invites = _StubMembers(_member(RoleCode.OWNER), owner_count=1), _StubInvites()
    with pytest.raises(LastOwnerError):
        await RemoveMemberInteractor(members, invites).remove(
            RemoveMemberCommand(ctx=CTX, member_id=12)
        )
    assert members.removed == []
    assert invites.revoked == []


async def test_없는_멤버는_MEMBER_NOT_FOUND_이고_초대도_그대로다():
    invites = _StubInvites()
    with pytest.raises(MemberNotFoundError):
        await RemoveMemberInteractor(_StubMembers(None), invites).remove(
            RemoveMemberCommand(ctx=CTX, member_id=99)
        )
    assert invites.revoked == []
