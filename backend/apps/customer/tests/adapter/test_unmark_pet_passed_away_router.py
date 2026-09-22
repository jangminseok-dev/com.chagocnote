from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.unmark_pet_passed_away_router import (
    unmark_pet_passed_away_router,
)
from customer.dependencies.unmark_pet_passed_away_provider import (
    get_unmark_pet_passed_away_use_case,
)
from customer.tests.helpers.api import NO_WRITE, STAFF, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def unmark_pet_passed_away(self, command):
        self.commands.append(command)
        return pet_detail_view()


async def _delete(stub, access):
    app = build_app(unmark_pet_passed_away_router, get_unmark_pet_passed_away_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete("/v1/shops/3/pets/101/passed-away")


async def test_직원도_무지개다리를_되돌린다():
    stub = _StubUseCase()
    assert (await _delete(stub, STAFF)).status_code == 200
    assert stub.commands[0].pet_id == 101


async def test_customer_write_가_없으면_403_이다():
    response = await _delete(_StubUseCase(), NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
