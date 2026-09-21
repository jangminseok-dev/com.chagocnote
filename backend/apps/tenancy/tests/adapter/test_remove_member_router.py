from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.remove_member_router import remove_member_router
from tenancy.dependencies.remove_member_provider import get_remove_member_use_case
from tenancy.domain.errors import LastOwnerError
from tenancy.tests.helpers.api import OWNER_PERMISSIONS, STAFF_PERMISSIONS, StubShopAccess, build_app


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def remove(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error


async def _delete(stub, access, path="/v1/shops/3/members/12"):
    app = build_app(remove_member_router, get_remove_member_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete(path)


async def test_사장은_멤버를_내보내고_204_를_받는다():
    stub = _StubUseCase()
    response = await _delete(stub, StubShopAccess(OWNER_PERMISSIONS))
    assert response.status_code == 204
    assert (stub.commands[0].ctx.shop_id, stub.commands[0].member_id) == (3, 12)


async def test_권한_없는_직원은_403_이다():
    stub = _StubUseCase()
    response = await _delete(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"))
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_int32_를_넘는_member_id_는_422_다():
    stub = _StubUseCase()
    response = await _delete(stub, StubShopAccess(OWNER_PERMISSIONS), "/v1/shops/3/members/99999999999")
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")
    assert stub.commands == []


async def test_마지막_사장을_내보내면_409_LAST_OWNER_다():
    stub = _StubUseCase(LastOwnerError("매장에는 사장이 한 명 이상 있어야 합니다."))
    response = await _delete(stub, StubShopAccess(OWNER_PERMISSIONS))
    assert (response.status_code, response.json()["code"]) == (409, "LAST_OWNER")
