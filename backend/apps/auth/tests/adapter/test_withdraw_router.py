from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.withdraw_router import withdraw_router
from auth.app.dtos.withdraw_dto import WithdrawResult
from auth.dependencies.provider_revoker_provider import get_provider_revoker
from auth.dependencies.recent_login_guard import RecentLogin, require_recent_login
from auth.dependencies.withdraw_provider import get_withdraw_use_case
from auth.domain.errors import UserNotFoundError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from core.database import get_db
from core.http_errors import install_error_handlers

KAKAO = IdentityRevocation(Provider.KAKAO, "kakao-100", None)


class _StubUseCase:
    def __init__(self, error=None, result=None):
        self.error = error
        self.result = result if result is not None else WithdrawResult(revocations=(KAKAO,))
        self.commands = []

    async def withdraw(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return self.result


class _StubRevoker:
    def __init__(self):
        self.revoked = []
        self.calls = 0

    async def revoke_all(self, identities):
        self.calls += 1
        self.revoked.extend(identities)


async def _no_db():
    yield None


def _app(stub, revoker, user_id=5):
    app = FastAPI()
    app.include_router(withdraw_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_withdraw_use_case] = lambda: stub
    app.dependency_overrides[get_provider_revoker] = lambda: revoker
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[require_recent_login] = lambda: RecentLogin(user_id=user_id, auth_time=1_700_000_000)
    return app


async def _delete(app, body=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        if body is None:
            return await client.delete("/v1/auth/account")
        return await client.request("DELETE", "/v1/auth/account", json=body)


async def test_탈퇴하면_204_이고_제공자_연결을_끊는다():
    stub, revoker = _StubUseCase(), _StubRevoker()
    response = await _delete(_app(stub, revoker), {"confirm_close_shops": True})
    assert response.status_code == 204
    assert (stub.commands[0].user_id, stub.commands[0].confirm_close_shops) == (5, True)
    assert revoker.revoked == [KAKAO]


async def test_본문이_없으면_매장_닫기를_확인하지_않은_것으로_본다():
    stub = _StubUseCase()
    response = await _delete(_app(stub, _StubRevoker()))
    assert response.status_code == 204
    assert stub.commands[0].confirm_close_shops is False


async def test_빈_본문도_매장_닫기를_확인하지_않은_것으로_본다():
    stub = _StubUseCase()
    response = await _delete(_app(stub, _StubRevoker()), {})
    assert response.status_code == 204
    assert stub.commands[0].confirm_close_shops is False


async def test_false를_명시해도_확인하지_않은_것으로_본다():
    stub = _StubUseCase()
    response = await _delete(_app(stub, _StubRevoker()), {"confirm_close_shops": False})
    assert response.status_code == 204
    assert stub.commands[0].confirm_close_shops is False


async def test_문자열_yes는_불리언이_아니라서_422_다():
    stub = _StubUseCase()
    response = await _delete(_app(stub, _StubRevoker()), {"confirm_close_shops": "yes"})
    assert response.status_code == 422
    assert stub.commands == []


async def test_숫자_1도_불리언이_아니라서_422_다():
    stub = _StubUseCase()
    response = await _delete(_app(stub, _StubRevoker()), {"confirm_close_shops": 1})
    assert response.status_code == 422
    assert stub.commands == []


async def test_이미_탈퇴해서_끊을_신원이_없으면_배경_작업을_걸지_않는다():
    """H5 — 두 번째 탈퇴 요청은 revocations=() 인 채로 끝난다. 빈 목록이어도 배경 작업을
    거는 것 자체는 낭비다."""
    stub = _StubUseCase(result=WithdrawResult(revocations=()))
    revoker = _StubRevoker()
    response = await _delete(_app(stub, revoker), {"confirm_close_shops": True})
    assert response.status_code == 204
    assert revoker.calls == 0


async def test_탈퇴가_실패하면_제공자_연결을_끊지_않는다():
    revoker = _StubRevoker()
    response = await _delete(_app(_StubUseCase(UserNotFoundError("다시 로그인해 주세요.")), revoker))
    assert response.status_code == 401
    assert revoker.revoked == []


async def test_로그인하지_않으면_401_이다():
    response = await _delete(_app(_StubUseCase(), _StubRevoker(), user_id=None))
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
