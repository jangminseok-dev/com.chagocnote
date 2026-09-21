from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.get_shop_router import get_shop_router
from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.dependencies.get_shop_provider import get_get_shop_use_case
from tenancy.tests.helpers.api import STAFF_PERMISSIONS, StubShopAccess, build_app


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def get_shop(self, query):
        self.queries.append(query)
        return ShopView(shop_id=3, name="Hiss Haus", business_type="pet_grooming",
                        phone=None, address=None, timezone="Asia/Seoul")


async def _get(stub, access, user_id=5):
    app = build_app(get_shop_router, get_get_shop_use_case, stub, access=access, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/v1/shops/3/settings")


async def test_직원도_매장_정보를_본다():
    stub = _StubUseCase()
    response = await _get(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"))
    assert response.status_code == 200
    assert response.json() == {
        "shop_id": 3, "name": "Hiss Haus", "business_type": "pet_grooming",
        "phone": None, "address": None, "timezone": "Asia/Seoul",
    }
    assert stub.queries[0].ctx.shop_id == 3


async def test_토큰이_없으면_401_이다():
    response = await _get(_StubUseCase(), StubShopAccess(), user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
