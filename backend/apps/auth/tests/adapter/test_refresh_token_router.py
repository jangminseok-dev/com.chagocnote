from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.refresh_token_router import refresh_token_router
from auth.app.dtos.token_dto import TokenPair
from auth.dependencies.refresh_token_provider import get_refresh_token_use_case
from auth.domain.errors import RefreshTokenReuseError
from core.http_errors import install_error_handlers


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def refresh(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return TokenPair("new-access", "new-refresh", 900)


def _client(stub):
    app = FastAPI()
    app.include_router(refresh_token_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_refresh_token_use_case] = lambda: stub
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_새_토큰_한_쌍을_돌려준다():
    stub = _StubUseCase()
    async with _client(stub) as client:
        response = await client.post("/v1/auth/refresh", json={"refresh_token": "old"})
    assert response.status_code == 200
    assert response.json() == {
        "access_token": "new-access", "refresh_token": "new-refresh",
        "token_type": "Bearer", "expires_in": 900,
    }
    assert stub.commands[0].refresh_token == "old"


async def test_재사용된_토큰은_401과_UNAUTHENTICATED_를_돌려준다():
    async with _client(_StubUseCase(RefreshTokenReuseError("다시 로그인해 주세요."))) as client:
        response = await client.post("/v1/auth/refresh", json={"refresh_token": "stolen"})
    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHENTICATED", "message": "다시 로그인해 주세요."}
