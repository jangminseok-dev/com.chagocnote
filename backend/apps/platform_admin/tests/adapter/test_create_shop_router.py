from datetime import datetime, timezone

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from hub.app.dtos.provisioned_shop import ProvisionedShop
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
from platform_admin.dependencies.create_shop_provider import get_create_shop_use_case
from platform_admin.dependencies.hub_ports import get_operator_directory

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def create_shop(self, command):
        self.commands.append(command)
        return ProvisionedShop(shop_id=3, name=command.name, owner_invite_code="ABCD2345",
                               invite_expires_at=EXPIRES)


class _StubOperators:
    """운영자 가드의 자리를 채운다. 5 번만 운영자다."""

    async def is_operator(self, user_id):
        return user_id == 5


async def _no_db():
    yield None


def _app(stub, user_id=5):
    app = FastAPI()
    app.include_router(create_shop_router)
    install_error_handlers(app, PLATFORM_ADMIN_ERROR_STATUS)
    app.dependency_overrides[get_create_shop_use_case] = lambda: stub
    app.dependency_overrides[get_operator_directory] = _StubOperators
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _post(app, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/platform/shops", json=body)


async def test_매장을_개설하면_201과_사장용_초대_코드를_돌려준다():
    stub = _StubUseCase()
    response = await _post(_app(stub), {"name": "  Hiss Haus  "})
    assert response.status_code == 201
    assert response.json() == {
        "shop_id": 3, "name": "Hiss Haus", "owner_invite_code": "ABCD2345",
        "invite_expires_at": "2026-09-27T12:00:00Z",
    }
    command = stub.commands[0]
    assert (command.name, command.business_type) == ("Hiss Haus", "pet_grooming")


async def test_이름이_비면_422_다():
    response = await _post(_app(_StubUseCase()), {"name": "   "})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_운영자가_아니면_403_이고_유스케이스를_부르지_않는다():
    stub = _StubUseCase()
    response = await _post(_app(stub, user_id=6), {"name": "Hiss Haus"})
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_토큰이_없으면_401_이다():
    response = await _post(_app(_StubUseCase(), user_id=None), {"name": "Hiss Haus"})
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
