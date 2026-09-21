from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.update_shop_router import update_shop_router
from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.dependencies.update_shop_provider import get_update_shop_use_case
from tenancy.tests.helpers.api import OWNER_PERMISSIONS, STAFF_PERMISSIONS, StubShopAccess, build_app


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def update_shop(self, command):
        self.commands.append(command)
        return ShopView(shop_id=3, name=command.name, business_type="pet_grooming",
                        phone=command.phone, address=command.address, timezone="Asia/Seoul")


async def _put(stub, access, body):
    app = build_app(update_shop_router, get_update_shop_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.put("/v1/shops/3/settings", json=body)


async def test_사장은_매장_정보를_고친다():
    stub = _StubUseCase()
    response = await _put(stub, StubShopAccess(OWNER_PERMISSIONS),
                          {"name": " 히스 하우스 ", "phone": "", "address": "서울 성동구"})
    assert response.status_code == 200
    assert response.json()["name"] == "히스 하우스"
    command = stub.commands[0]
    # 빈 문자열로 온 전화번호는 "없음"으로 저장한다.
    assert (command.ctx.shop_id, command.name, command.phone, command.address) == (
        3, "히스 하우스", None, "서울 성동구",
    )


async def test_권한_없는_직원은_403_이다():
    stub = _StubUseCase()
    response = await _put(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"), {"name": "새 이름"})
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_이름이_비면_422_다():
    response = await _put(_StubUseCase(), StubShopAccess(OWNER_PERMISSIONS), {"name": "  "})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")
