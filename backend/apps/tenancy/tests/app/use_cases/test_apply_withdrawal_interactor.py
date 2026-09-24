from datetime import datetime, timezone

import pytest

from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.entities.shop import Shop
from hub.app.errors import (
    WithdrawalOwnershipTransferRequiredError,
    WithdrawalShopCloseConfirmRequiredError,
)
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _member(member_id, shop_id, role):
    return Member(id=member_id, shop_id=shop_id, user_id=5, role=role, joined_at=NOW)


class _StubMembers:
    """memberships: 잠그기 전에 읽은 소속. under_lock: 잠근 뒤 다시 읽었을 때의 소속(기본은 같다)."""

    def __init__(self, memberships, owners=None, actives=None, under_lock=None):
        self.memberships = memberships
        self.under_lock = under_lock if under_lock is not None else {m.id: m for m in memberships}
        self.owners = owners or {}
        self.actives = actives or {}
        self.calls = []
        self.removed = []

    async def list_active_for_user(self, user_id):
        return self.memberships

    async def lock_membership_changes(self, shop_id):
        self.calls.append(("lock", shop_id))

    async def get_active(self, ctx, member_id):
        self.calls.append(("get_active", ctx.shop_id))
        return self.under_lock.get(member_id)

    async def count_owners(self, ctx):
        return self.owners.get(ctx.shop_id, 1)

    async def count_active(self, ctx):
        return self.actives.get(ctx.shop_id, 1)

    async def remove(self, ctx, member_id):
        self.removed.append((ctx.shop_id, member_id))


class _StubShops:
    def __init__(self, closed_shop_ids=()):
        self.closed_shop_ids = set(closed_shop_ids)
        self.closed = []

    async def get(self, ctx):
        return Shop(id=ctx.shop_id, name=f"매장 {ctx.shop_id}", business_type="pet_grooming",
                    phone=None, address=None, timezone="Asia/Seoul", suspended_at=None,
                    closed_at=NOW if ctx.shop_id in self.closed_shop_ids else None)

    async def close(self, ctx):
        self.closed.append(ctx.shop_id)


class _StubInvites:
    def __init__(self):
        self.revoked = []

    async def revoke_created_by(self, ctx, member_id):
        self.revoked.append((ctx.shop_id, member_id))


def _run(members, shops=None):
    shops, invites = shops or _StubShops(), _StubInvites()
    return ApplyWithdrawalInteractor(members, shops, invites), shops, invites


async def test_직원은_소속을_해제하고_만들어_둔_초대를_무효화한다():
    members = _StubMembers([_member(21, 3, RoleCode.STAFF)])
    interactor, shops, invites = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == [(3, 21)]
    assert invites.revoked == [(3, 21)]   # F2
    assert shops.closed == []


async def test_다른_사장이_있으면_사장도_그냥_나간다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 2}, actives={3: 2})
    interactor, shops, _ = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == [(3, 21)] and shops.closed == []


async def test_혼자_사장인_매장에_다른_멤버가_있으면_막는다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 2})
    interactor, shops, _ = _run(members)
    with pytest.raises(WithdrawalOwnershipTransferRequiredError) as exc:
        await interactor.apply_withdrawal(5, close_sole_owned=True)   # 확인을 줬어도 막는다
    assert "매장 3" in str(exc.value)
    assert members.removed == [] and shops.closed == []


async def test_혼자뿐인_매장은_확인_없이는_닫지_않는다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 1})
    interactor, shops, _ = _run(members)
    with pytest.raises(WithdrawalShopCloseConfirmRequiredError) as exc:
        await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert "매장 3" in str(exc.value)
    assert members.removed == [] and shops.closed == []


async def test_혼자뿐인_매장은_확인이_있으면_닫고_나간다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 1})
    interactor, shops, invites = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=True)
    assert shops.closed == [3]
    assert members.removed == [(3, 21)] and invites.revoked == [(3, 21)]


async def test_이미_닫힌_매장은_규칙을_따지지_않고_나간다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 2})
    interactor, shops, _ = _run(members, _StubShops(closed_shop_ids=[3]))
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == [(3, 21)] and shops.closed == []


async def test_매장을_ID_순서로_잠그고_잠근_뒤에_대상을_읽는다():
    """F3 — 리포지토리가 매장 ID 순으로 돌려준 순서 그대로, 매장마다 잠금이 먼저다."""
    members = _StubMembers([_member(21, 3, RoleCode.STAFF), _member(34, 8, RoleCode.STAFF)])
    interactor, _, _ = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.calls == [("lock", 3), ("get_active", 3), ("lock", 8), ("get_active", 8)]


async def test_잠근_뒤에_다시_읽은_역할로_판단한다():
    """F1 — 목록을 읽을 때는 직원이었지만, 잠그는 사이에 혼자 남은 사장이 되었다."""
    members = _StubMembers(
        [_member(21, 3, RoleCode.STAFF)],
        under_lock={21: _member(21, 3, RoleCode.OWNER)}, owners={3: 1}, actives={3: 2},
    )
    interactor, _, _ = _run(members)
    with pytest.raises(WithdrawalOwnershipTransferRequiredError):
        await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == []


async def test_잠그는_사이에_내보내졌으면_건너뛴다():
    members = _StubMembers([_member(21, 3, RoleCode.STAFF)], under_lock={})
    interactor, _, invites = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == [] and invites.revoked == []


async def test_소속이_없으면_아무것도_하지_않는다():
    members = _StubMembers([])
    interactor, shops, _ = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.calls == [] and shops.closed == []
