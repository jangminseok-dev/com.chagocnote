from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.accept_invite_router import accept_invite_router
from tenancy.app.dtos.accept_invite_dto import AcceptInviteResult
from tenancy.dependencies.accept_invite_provider import get_accept_invite_use_case
from tenancy.domain.errors import AccountUnavailableError, InviteExpiredError, TooManyAttemptsError
from tenancy.tests.helpers.api import build_app


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def accept(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return AcceptInviteResult(shop_id=3, shop_name="Hiss Haus", role="owner", member_id=21)


async def _post(stub, body, user_id=5):
    app = build_app(accept_invite_router, get_accept_invite_use_case, stub, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/invites/accept", json=body)


async def test_합류하면_매장과_역할을_돌려준다():
    stub = _StubUseCase()
    response = await _post(stub, {"code": "abcd-2345"})
    assert response.status_code == 200
    assert response.json() == {"shop_id": 3, "shop_name": "Hiss Haus", "role": "owner", "member_id": 21}
    assert (stub.commands[0].user_id, stub.commands[0].code) == (5, "abcd-2345")


async def test_만료된_코드는_400_INVITE_EXPIRED_다():
    response = await _post(_StubUseCase(InviteExpiredError("만료된 초대 코드입니다.")), {"code": "ABCD2345"})
    assert (response.status_code, response.json()["code"]) == (400, "INVITE_EXPIRED")


async def test_시도가_너무_많으면_429_TOO_MANY_ATTEMPTS_다():
    response = await _post(_StubUseCase(TooManyAttemptsError("잠시 뒤에 다시 시도해 주세요.")), {"code": "ABCD2345"})
    assert (response.status_code, response.json()["code"]) == (429, "TOO_MANY_ATTEMPTS")


async def test_잠근_뒤에_보니_탈퇴한_유저면_401_UNAUTHENTICATED_다():
    response = await _post(_StubUseCase(AccountUnavailableError("다시 로그인해 주세요.")), {"code": "ABCD2345"})
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")


async def test_코드가_비면_422_다():
    response = await _post(_StubUseCase(), {"code": "  "})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_토큰이_없으면_401_이다():
    response = await _post(_StubUseCase(), {"code": "ABCD2345"}, user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
