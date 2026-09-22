from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.add_pet_router import add_pet_router
from customer.dependencies.add_pet_provider import get_add_pet_use_case
from customer.tests.helpers.api import NO_WRITE, PET_BODY, STAFF, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def add_pet(self, command):
        self.commands.append(command)
        return pet_detail_view()


async def _post(stub, access):
    app = build_app(add_pet_router, get_add_pet_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/shops/3/customers/1/pets", json=PET_BODY)


async def test_직원도_반려동물을_더하고_201_과_반려동물_상세를_받는다():
    stub = _StubUseCase()
    response = await _post(stub, STAFF)
    assert response.status_code == 201
    assert response.json()["owner"]["phone_masked"] == "010-12··-5678"
    assert (stub.commands[0].customer_id, stub.commands[0].pet.name) == (1, "콩이")


async def test_customer_write_가_없으면_403_이다():
    stub = _StubUseCase()
    response = await _post(stub, NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []
