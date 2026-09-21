from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.create_invite_router import create_invite_router
from tenancy.app.dtos.create_invite_dto import CreatedInvite
from tenancy.dependencies.create_invite_provider import get_create_invite_use_case
from tenancy.tests.helpers.api import OWNER_PERMISSIONS, STAFF_PERMISSIONS, StubShopAccess, build_app

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def create(self, command):
        self.commands.append(command)
        return CreatedInvite(code="ABCD2345", role="staff", expires_at=EXPIRES)


async def _post(stub, access, user_id=5):
    app = build_app(create_invite_router, get_create_invite_use_case, stub, access=access, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/shops/3/invites")


async def test_사장은_초대_코드를_받는다():
    stub, access = _StubUseCase(), StubShopAccess(OWNER_PERMISSIONS)
    response = await _post(stub, access)
    assert response.status_code == 201
    assert response.json() == {"code": "ABCD2345", "role": "staff", "expires_at": "2026-09-27T12:00:00Z"}
    assert access.calls == [(5, 3)]
    assert stub.commands[0].ctx.shop_id == 3


async def test_권한_없는_직원은_403_이고_유스케이스를_부르지_않는다():
    stub = _StubUseCase()
    response = await _post(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"))
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_토큰이_없으면_401_이다():
    response = await _post(_StubUseCase(), StubShopAccess(OWNER_PERMISSIONS), user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
