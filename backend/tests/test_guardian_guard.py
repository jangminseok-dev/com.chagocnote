from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from core.guardian_guard import get_guardian_access_port, get_guardian_context
from core.hub_errors import HUB_ERROR_STATUS
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from hub.app.dtos.guardian import GuardianContext
from hub.app.errors import GuardianAccessDeniedError


class _StubAccess:
    def __init__(self):
        self.calls = []

    async def resolve(self, user_id, link_id):
        self.calls.append((user_id, link_id))
        if link_id == 404:
            raise GuardianAccessDeniedError("연결을 찾을 수 없습니다.")
        return GuardianContext(link_id=link_id, user_id=user_id, shop_id=3, customer_id=7)


def _app(stub):
    app = FastAPI()
    install_error_handlers(app, HUB_ERROR_STATUS)

    @app.get("/v1/me/guardian/links/{link_id}/thing")
    async def route(ctx: GuardianContext = Depends(get_guardian_context)) -> dict:
        return {"shop_id": ctx.shop_id, "customer_id": ctx.customer_id}

    app.dependency_overrides[get_current_user_id] = lambda: 5
    app.dependency_overrides[get_guardian_access_port] = lambda: stub
    return app


async def _get(app, path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_경로의_link_id_와_로그인한_계정으로_연결을_확인한다():
    stub = _StubAccess()
    response = await _get(_app(stub), "/v1/me/guardian/links/9/thing")
    assert response.json() == {"shop_id": 3, "customer_id": 7}
    assert stub.calls == [(5, 9)]


async def test_내_연결이_아니면_404_GUARDIAN_LINK_NOT_FOUND_다():
    response = await _get(_app(_StubAccess()), "/v1/me/guardian/links/404/thing")
    assert (response.status_code, response.json()["code"]) == (404, "GUARDIAN_LINK_NOT_FOUND")


async def test_int32_를_넘는_link_id_는_DB_에_닿기_전에_422_다():
    stub = _StubAccess()
    response = await _get(_app(stub), "/v1/me/guardian/links/99999999999/thing")
    assert response.status_code == 422 and stub.calls == []
