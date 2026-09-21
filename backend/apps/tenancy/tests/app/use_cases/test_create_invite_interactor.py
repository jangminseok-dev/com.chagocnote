from datetime import datetime, timedelta, timezone

import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.create_invite_dto import CreateInviteCommand
from tenancy.app.use_cases.create_invite_interactor import CreateInviteInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.errors import NotAMemberError
from tenancy.domain.services.invite_code import hash_invite_code
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"member:manage"}))


def _member(role=RoleCode.OWNER):
    return Member(id=11, shop_id=3, user_id=2, role=role, joined_at=NOW)


class _StubMembers:
    """잠근 뒤 다시 읽는 행위자를 돌려준다. actor 가 None 이면 소속이 끊긴 것이다."""

    def __init__(self, actor):
        self.actor = actor
        self.calls = []

    async def lock_membership_changes(self, shop_id):
        self.calls.append("lock_membership_changes")
        self.locked_shop_id = shop_id

    async def get_active(self, ctx, member_id):
        self.calls.append("get_active")
        self.read_member_id = member_id
        return self.actor


class _StubInvites:
    def __init__(self):
        self.created = []

    async def create(self, ctx, role, code_hash, expires_at, max_uses):
        self.created.append((ctx, role, code_hash, expires_at, max_uses))


def _interactor(members, invites):
    return CreateInviteInteractor(members=members, invites=invites, now=lambda: NOW)


async def test_직원용_1회_초대를_7일_기한으로_만든다():
    invites = _StubInvites()
    result = await _interactor(_StubMembers(_member()), invites).create(CreateInviteCommand(ctx=CTX))
    ctx, role, code_hash, expires_at, max_uses = invites.created[0]
    assert (ctx, role, max_uses) == (CTX, RoleCode.STAFF, 1)
    assert expires_at == NOW + timedelta(days=7)
    assert code_hash == hash_invite_code(result.code)
    assert (len(result.code), result.role, result.expires_at) == (8, "staff", expires_at)


async def test_초대를_만들기_전에_매장_행을_잠그고_행위자를_다시_읽는다():
    """F-I2"""
    members, invites = _StubMembers(_member()), _StubInvites()
    await _interactor(members, invites).create(CreateInviteCommand(ctx=CTX))
    assert members.calls == ["lock_membership_changes", "get_active"]
    assert (members.locked_shop_id, members.read_member_id) == (3, 11)


async def test_잠근_뒤에_소속이_끊긴_행위자면_초대를_만들지_않는다():
    members, invites = _StubMembers(None), _StubInvites()
    with pytest.raises(NotAMemberError):
        await _interactor(members, invites).create(CreateInviteCommand(ctx=CTX))
    assert invites.created == []


async def test_잠근_뒤에_역할이_낮춰진_행위자면_초대를_만들지_않는다():
    members, invites = _StubMembers(_member(RoleCode.STAFF)), _StubInvites()
    with pytest.raises(NotAMemberError):
        await _interactor(members, invites).create(CreateInviteCommand(ctx=CTX))
    assert invites.created == []
