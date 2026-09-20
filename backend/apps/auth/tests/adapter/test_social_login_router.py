from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.social_login_router import social_login_router
from auth.app.dtos.social_login_dto import SocialLoginResult
from auth.app.dtos.token_dto import TokenPair
from auth.dependencies.social_login_provider import get_social_login_use_case
from auth.domain.errors import AccountSuspendedError, ProviderVerificationError
from core.http_errors import install_error_handlers


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def login(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return SocialLoginResult(user_id=7, is_new_user=True, tokens=TokenPair("access", "refresh", 900))


def _client(stub):
    app = FastAPI()
    app.include_router(social_login_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_social_login_use_case] = lambda: stub
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_로그인에_성공하면_토큰_한_쌍을_돌려준다():
    stub = _StubUseCase()
    async with _client(stub) as client:
        response = await client.post("/v1/auth/social", json={"provider": "dev", "token": "owner"})
    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access", "refresh_token": "refresh", "token_type": "Bearer",
        "expires_in": 900, "user_id": 7, "is_new_user": True,
    }
    assert stub.commands[0].provider == "dev"
    assert stub.commands[0].authorization_code is None


async def test_정지된_계정은_403과_오류_코드를_돌려준다():
    async with _client(_StubUseCase(AccountSuspendedError("정지된 계정입니다."))) as client:
        response = await client.post("/v1/auth/social", json={"provider": "dev", "token": "x"})
    assert response.status_code == 403
    assert response.json() == {"code": "ACCOUNT_SUSPENDED", "message": "정지된 계정입니다."}


async def test_제공자_검증에_실패하면_401이다():
    async with _client(_StubUseCase(ProviderVerificationError("확인할 수 없습니다."))) as client:
        response = await client.post("/v1/auth/social", json={"provider": "kakao", "token": "bad"})
    assert response.status_code == 401
    assert response.json()["code"] == "PROVIDER_VERIFICATION_FAILED"


async def test_token_이_없으면_422이다():
    async with _client(_StubUseCase()) as client:
        response = await client.post("/v1/auth/social", json={"provider": "dev"})
    assert response.status_code == 422
