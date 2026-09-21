from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.link_identity_router import link_identity_router
from auth.app.dtos.link_identity_dto import LinkedIdentities
from auth.dependencies.link_identity_provider import get_link_identity_use_case
from auth.domain.errors import (
    IdentityAlreadyLinkedError,
    ProviderAlreadyLinkedError,
    UnsupportedProviderError,
)
from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def link(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return LinkedIdentities(identities=("kakao", "apple"))


async def _no_db():
    yield None


def _app(stub, user_id=5):
    app = FastAPI()
    app.include_router(link_identity_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_link_identity_use_case] = lambda: stub
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _post(app, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/auth/identities", json=body)


async def test_연결하면_로그인_수단_목록을_돌려준다():
    stub = _StubUseCase()
    response = await _post(_app(stub), {"provider": "apple", "token": "id-token",
                                       "authorization_code": "code", "nonce": "raw"})
    assert (response.status_code, response.json()) == (200, {"identities": ["kakao", "apple"]})
    command = stub.commands[0]
    assert (command.user_id, command.provider, command.token) == (5, "apple", "id-token")
    assert (command.authorization_code, command.nonce) == ("code", "raw")


async def test_이미_다른_계정에_붙은_신원은_409_다():
    stub = _StubUseCase(IdentityAlreadyLinkedError("이미 다른 계정에 연결된 로그인 수단입니다."))
    response = await _post(_app(stub), {"provider": "kakao", "token": "t"})
    assert (response.status_code, response.json()["code"]) == (409, "IDENTITY_ALREADY_LINKED")


async def test_토큰이_비면_422_다():
    response = await _post(_app(_StubUseCase()), {"provider": "kakao", "token": ""})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_제공자가_비면_422_다():
    response = await _post(_app(_StubUseCase()), {"provider": "", "token": "x"})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_이미_연결된_제공자는_409_다():
    stub = _StubUseCase(ProviderAlreadyLinkedError("kakao 로그인은 이미 연결되어 있습니다."))
    response = await _post(_app(stub), {"provider": "kakao", "token": "t"})
    assert (response.status_code, response.json()["code"]) == (409, "PROVIDER_ALREADY_LINKED")


async def test_지원하지_않는_제공자는_400_이다():
    stub = _StubUseCase(UnsupportedProviderError("naver 로그인은 지원하지 않습니다."))
    response = await _post(_app(stub), {"provider": "naver", "token": "t"})
    assert (response.status_code, response.json()["code"]) == (400, "PROVIDER_NOT_SUPPORTED")


async def test_로그인하지_않으면_401_이다():
    response = await _post(_app(_StubUseCase(), user_id=None), {"provider": "kakao", "token": "t"})
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
