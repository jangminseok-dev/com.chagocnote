from datetime import datetime, timedelta, timezone

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.create_invite_dto import CreateInviteCommand
from tenancy.app.use_cases.create_invite_interactor import CreateInviteInteractor
from tenancy.domain.services.invite_code import hash_invite_code
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"member:manage"}))


class _StubInvites:
    def __init__(self):
        self.created = []

    async def create(self, ctx, role, code_hash, expires_at, max_uses):
        self.created.append((ctx, role, code_hash, expires_at, max_uses))


async def test_직원용_1회_초대를_7일_기한으로_만든다():
    invites = _StubInvites()
    result = await CreateInviteInteractor(invites, now=lambda: NOW).create(CreateInviteCommand(ctx=CTX))
    ctx, role, code_hash, expires_at, max_uses = invites.created[0]
    assert (ctx, role, max_uses) == (CTX, RoleCode.STAFF, 1)
    assert expires_at == NOW + timedelta(days=7)
    assert code_hash == hash_invite_code(result.code)
    assert (len(result.code), result.role, result.expires_at) == (8, "staff", expires_at)
