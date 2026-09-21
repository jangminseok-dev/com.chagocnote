from datetime import datetime, timezone

import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand
from tenancy.app.use_cases.remove_member_interactor import RemoveMemberInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.errors import LastOwnerError, MemberNotFoundError
from tenancy.domain.value_objects.role_code import RoleCode

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"member:manage"}))


class _StubMembers:
    def __init__(self, target, owner_count=1):
        self.target = target
        self.owner_count = owner_count
        self.removed = []

    async def get_active(self, ctx, member_id):
        return self.target

    async def count_owners(self, ctx):
        return self.owner_count

    async def remove(self, ctx, member_id):
        self.removed.append((ctx, member_id))


def _member(role):
    return Member(id=12, shop_id=3, user_id=2, role=role, joined_at=JOINED)


async def test_직원을_내보낸다():
    members = _StubMembers(_member(RoleCode.STAFF))
    await RemoveMemberInteractor(members).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.removed == [(CTX, 12)]


async def test_사장이_둘이면_한_명을_내보낼_수_있다():
    members = _StubMembers(_member(RoleCode.OWNER), owner_count=2)
    await RemoveMemberInteractor(members).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.removed == [(CTX, 12)]


async def test_마지막_사장은_내보낼_수_없다():
    members = _StubMembers(_member(RoleCode.OWNER), owner_count=1)
    with pytest.raises(LastOwnerError):
        await RemoveMemberInteractor(members).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.removed == []


async def test_없는_멤버는_MEMBER_NOT_FOUND_다():
    with pytest.raises(MemberNotFoundError):
        await RemoveMemberInteractor(_StubMembers(None)).remove(RemoveMemberCommand(ctx=CTX, member_id=99))
