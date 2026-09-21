from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfResponse
from platform_admin.dependencies.hub_ports import get_operator_directory
from platform_admin.dependencies.platform_myself_provider import get_platform_myself_use_case


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def introduce_myself(self, query):
        self.queries.append(query)
        return PlatformMyselfResponse(
            id=query.id, name=query.name, introduction="POST /v1/platform/shops"
        )


class _StubOperators:
    """운영자 가드의 자리를 채운다. 5 번만 운영자다."""

    async def is_operator(self, user_id):
        return user_id == 5


async def _no_db():
    yield None


def _app(stub, user_id=None):
    app = FastAPI()
    app.include_router(platform_myself_router)
    install_error_handlers(app, PLATFORM_ADMIN_ERROR_STATUS)
    app.dependency_overrides[get_platform_myself_use_case] = lambda: stub
    app.dependency_overrides[get_operator_directory] = _StubOperators
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _get(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/v1/platform/myself")


async def test_운영자는_자기소개를_받는다():
    response = await _get(_app(_StubUseCase(), user_id=5))
    assert response.status_code == 200
    assert response.json()["name"] == "플랫폼 운영 (platform_admin)"


async def test_운영자가_아니면_403_PERMISSION_DENIED_이고_유스케이스를_부르지_않는다():
    stub = _StubUseCase()
    response = await _get(_app(stub, user_id=6))
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.queries == []


async def test_토큰이_없으면_401_이다():
    response = await _get(_app(_StubUseCase()))
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
