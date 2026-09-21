from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.unlink_identity_router import unlink_identity_router
from auth.app.dtos.token_dto import TokenPair
from auth.app.dtos.unlink_identity_dto import UnlinkIdentityResult
from auth.dependencies.provider_revoker_provider import get_provider_revoker
from auth.dependencies.unlink_identity_provider import get_unlink_identity_use_case
from auth.domain.errors import IdentityNotFoundError, LastIdentityError, UnsupportedProviderError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id

APPLE = IdentityRevocation(Provider.APPLE, "apple-1", "apple-refresh")


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def unlink(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return UnlinkIdentityResult(
            identities=("kakao",), tokens=TokenPair("new-access", "5.new-refresh", 900), revocation=APPLE
        )


class _StubRevoker:
    def __init__(self):
        self.revoked = []

    async def revoke_all(self, identities):
        self.revoked.extend(identities)


async def _no_db():
    yield None


def _app(stub, revoker, user_id=5):
    app = FastAPI()
    app.include_router(unlink_identity_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_unlink_identity_use_case] = lambda: stub
    app.dependency_overrides[get_provider_revoker] = lambda: revoker
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _delete(app, provider="apple"):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete(f"/v1/auth/identities/{provider}")


async def test_해제하면_남은_수단과_새_토큰을_돌려주고_제공자_연결을_끊는다():
    stub, revoker = _StubUseCase(), _StubRevoker()
    response = await _delete(_app(stub, revoker))
    assert response.status_code == 200
    assert response.json() == {
        "identities": ["kakao"], "access_token": "new-access", "refresh_token": "5.new-refresh",
        "token_type": "Bearer", "expires_in": 900,
    }
    assert (stub.commands[0].user_id, stub.commands[0].provider) == (5, "apple")
    assert revoker.revoked == [APPLE]


async def test_마지막_수단이면_409_이고_제공자_연결을_끊지_않는다():
    revoker = _StubRevoker()
    response = await _delete(_app(_StubUseCase(LastIdentityError("마지막 로그인 수단입니다.")), revoker))
    assert (response.status_code, response.json()["code"]) == (409, "LAST_IDENTITY")
    assert revoker.revoked == []


async def test_로그인하지_않으면_401_이다():
    response = await _delete(_app(_StubUseCase(), _StubRevoker(), user_id=None))
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")


async def test_모르는_제공자는_400_이고_제공자_연결을_끊지_않는다():
    revoker = _StubRevoker()
    error = UnsupportedProviderError("naver 로그인은 지원하지 않습니다.")
    response = await _delete(_app(_StubUseCase(error), revoker), provider="naver")
    assert (response.status_code, response.json()["code"]) == (400, "PROVIDER_NOT_SUPPORTED")
    assert revoker.revoked == []


async def test_연결되지_않은_수단은_404_이고_제공자_연결을_끊지_않는다():
    revoker = _StubRevoker()
    error = IdentityNotFoundError("google 로그인은 연결되어 있지 않습니다.")
    response = await _delete(_app(_StubUseCase(error), revoker), provider="google")
    assert (response.status_code, response.json()["code"]) == (404, "IDENTITY_NOT_FOUND")
    assert revoker.revoked == []
