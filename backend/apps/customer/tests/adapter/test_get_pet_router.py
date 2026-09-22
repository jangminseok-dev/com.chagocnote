from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.get_pet_router import get_pet_router
from customer.dependencies.get_pet_provider import get_get_pet_use_case
from customer.tests.helpers.api import NO_WRITE, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def get_pet(self, query):
        self.queries.append(query)
        return pet_detail_view()


async def test_멤버는_반려동물_상세를_보고_보호자_번호는_가려져_있다():
    stub = _StubUseCase()
    app = build_app(get_pet_router, get_get_pet_use_case, stub, access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/shops/3/pets/101")
    assert response.status_code == 200
    assert response.json()["owner"] == {"customer_id": 1, "name": "김민지", "phone_masked": "010-12··-5678"}
    assert (stub.queries[0].ctx.shop_id, stub.queries[0].pet_id) == (3, 101)
