from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.get_me_router import get_me_router
from auth.app.dtos.get_me_dto import MeResponse
from auth.dependencies.get_me_provider import get_get_me_use_case
from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def get_me(self, query):
        self.queries.append(query)
        return MeResponse(id=query.user_id, display_name="두부 보호자",
                          profile_image_url=None, identities=("kakao",))


async def _no_db():
    yield None


def _app(stub):
    app = FastAPI()
    app.include_router(get_me_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_get_me_use_case] = lambda: stub
    app.dependency_overrides[get_db] = _no_db
    return app


async def test_로그인한_유저의_정보를_돌려준다():
    stub = _StubUseCase()
    app = _app(stub)
    app.dependency_overrides[get_current_user_id] = lambda: 5
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/me")
    assert response.status_code == 200
    assert response.json() == {
        "id": 5, "display_name": "두부 보호자", "profile_image_url": None, "identities": ["kakao"],
    }
    assert stub.queries[0].user_id == 5


async def test_토큰이_없으면_401과_UNAUTHENTICATED_다():
    async with AsyncClient(transport=ASGITransport(app=_app(_StubUseCase())), base_url="http://t") as client:
        response = await client.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
