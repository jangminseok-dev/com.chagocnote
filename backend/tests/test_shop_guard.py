import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port, get_shop_context, require_permission
from hub.app.dtos.shop_context import ShopContext


class _StubAccess:
    def __init__(self, permissions):
        self.permissions = frozenset(permissions)
        self.calls = []

    async def resolve(self, user_id, shop_id):
        self.calls.append((user_id, shop_id))
        return ShopContext(shop_id=shop_id, member_id=11, role="staff", permissions=self.permissions)


def _app(stub):
    app = FastAPI()
    install_error_handlers(app, {})

    @app.get("/v1/shops/{shop_id}/open")
    async def open_route(ctx: ShopContext = Depends(get_shop_context)) -> dict:
        return {"shop_id": ctx.shop_id, "member_id": ctx.member_id}

    @app.get("/v1/shops/{shop_id}/managed")
    async def managed_route(ctx: ShopContext = Depends(require_permission("member:manage"))) -> dict:
        return {"member_id": ctx.member_id}

    app.dependency_overrides[get_current_user_id] = lambda: 5
    if stub is not None:
        app.dependency_overrides[get_shop_access_port] = lambda: stub
    return app


async def _get(app, path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_소속만_확인하는_경로는_경로의_shop_id_로_컨텍스트를_만든다():
    stub = _StubAccess([])
    response = await _get(_app(stub), "/v1/shops/3/open")
    assert (response.status_code, response.json()) == (200, {"shop_id": 3, "member_id": 11})
    assert stub.calls == [(5, 3)]


async def test_권한이_있으면_통과한다():
    response = await _get(_app(_StubAccess(["member:manage"])), "/v1/shops/3/managed")
    assert response.status_code == 200


async def test_권한이_없으면_403_PERMISSION_DENIED_다():
    response = await _get(_app(_StubAccess(["record:write"])), "/v1/shops/3/managed")
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")


async def test_자리를_채우지_않으면_바로_드러난다():
    with pytest.raises(RuntimeError, match="ShopAccessPort"):
        await _get(_app(None), "/v1/shops/3/open")
