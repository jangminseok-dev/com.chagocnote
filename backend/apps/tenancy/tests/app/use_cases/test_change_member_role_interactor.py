from datetime import datetime, timezone

import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.change_member_role_dto import ChangeMemberRoleCommand
from tenancy.app.use_cases.change_member_role_interactor import ChangeMemberRoleInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.errors import LastOwnerError, MemberNotFoundError
from tenancy.domain.value_objects.role_code import RoleCode

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"member:manage"}))


class _StubMembers:
    def __init__(self, target, owner_count=1):
        self.target = target
        self.owner_count = owner_count
        self.counted = 0
        self.changes = []
        self.calls = []

    async def lock_membership_changes(self, ctx):
        self.calls.append("lock_membership_changes")

    async def get_active(self, ctx, member_id):
        self.calls.append("get_active")
        return self.target

    async def count_owners(self, ctx):
        self.counted += 1
        return self.owner_count

    async def change_role(self, ctx, member_id, role):
        self.changes.append((ctx, member_id, role))


class _StubInvites:
    def __init__(self):
        self.revoked = []

    async def revoke_created_by(self, ctx, member_id):
        self.revoked.append((ctx, member_id))


def _member(role):
    return Member(id=12, shop_id=3, user_id=2, role=role, joined_at=JOINED)


def _command(role):
    return ChangeMemberRoleCommand(ctx=CTX, member_id=12, role=role)


async def test_직원을_사장으로_올릴_때는_사장_수를_세지_않고_초대도_그대로다():
    members, invites = _StubMembers(_member(RoleCode.STAFF)), _StubInvites()
    result = await ChangeMemberRoleInteractor(members, invites).change_role(_command("owner"))
    assert members.changes == [(CTX, 12, RoleCode.OWNER)]
    assert members.counted == 0
    assert invites.revoked == []
    assert (result.member_id, result.user_id, result.role) == (12, 2, "owner")


async def test_대상을_읽기_전에_매장_행을_잠근다():
    members, invites = _StubMembers(_member(RoleCode.STAFF)), _StubInvites()
    await ChangeMemberRoleInteractor(members, invites).change_role(_command("owner"))
    assert members.calls[:2] == ["lock_membership_changes", "get_active"]


async def test_같은_역할로_바꿔도_매장_행은_먼저_잠근다():
    members, invites = _StubMembers(_member(RoleCode.STAFF)), _StubInvites()
    await ChangeMemberRoleInteractor(members, invites).change_role(_command("staff"))
    assert members.calls == ["lock_membership_changes", "get_active"]


async def test_사장을_직원으로_낮추면_그가_만든_초대를_무효화한다():
    members, invites = _StubMembers(_member(RoleCode.OWNER), owner_count=2), _StubInvites()
    result = await ChangeMemberRoleInteractor(members, invites).change_role(_command("staff"))
    assert members.changes == [(CTX, 12, RoleCode.STAFF)]
    assert invites.revoked == [(CTX, 12)]
    assert result.role == "staff"


async def test_마지막_사장은_낮출_수_없고_초대도_그대로다():
    members, invites = _StubMembers(_member(RoleCode.OWNER), owner_count=1), _StubInvites()
    with pytest.raises(LastOwnerError):
        await ChangeMemberRoleInteractor(members, invites).change_role(_command("staff"))
    assert members.changes == []
    assert invites.revoked == []


async def test_같은_역할로_바꾸면_아무것도_하지_않는다():
    members, invites = _StubMembers(_member(RoleCode.STAFF)), _StubInvites()
    result = await ChangeMemberRoleInteractor(members, invites).change_role(_command("staff"))
    assert members.changes == [] and result.role == "staff"
    assert invites.revoked == []


async def test_없는_멤버는_MEMBER_NOT_FOUND_이고_초대도_그대로다():
    invites = _StubInvites()
    with pytest.raises(MemberNotFoundError):
        await ChangeMemberRoleInteractor(_StubMembers(None), invites).change_role(_command("owner"))
    assert invites.revoked == []
