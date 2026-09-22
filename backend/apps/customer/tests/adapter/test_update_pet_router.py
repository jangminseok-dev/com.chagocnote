from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
from customer.dependencies.update_pet_provider import get_update_pet_use_case
from customer.tests.helpers.api import NO_WRITE, PET_BODY, STAFF, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def update_pet(self, command):
        self.commands.append(command)
        return pet_detail_view()


async def _put(stub, body, access):
    app = build_app(update_pet_router, get_update_pet_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.put("/v1/shops/3/pets/101", json=body)


async def test_직원도_반려동물을_고친다():
    stub = _StubUseCase()
    body = {**PET_BODY, "birth_year": None, "birth_date": "2021-03-01", "conditions": [],
            "no_known_conditions": True}
    response = await _put(stub, body, STAFF)
    assert response.status_code == 200
    command = stub.commands[0]
    assert (command.pet_id, str(command.pet.birth_date), command.pet.conditions) == (101, "2021-03-01", ())


async def test_customer_write_가_없으면_403_이다():
    stub = _StubUseCase()
    response = await _put(stub, PET_BODY, NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
