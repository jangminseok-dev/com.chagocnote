from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.delete_pet_router import delete_pet_router
from customer.dependencies.delete_pet_provider import get_delete_pet_use_case
from customer.domain.errors import LastPetError
from customer.tests.helpers.api import NO_WRITE, STAFF, build_app


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def delete_pet(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error


async def _delete(stub, access):
    app = build_app(delete_pet_router, get_delete_pet_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete("/v1/shops/3/pets/101")


async def test_직원도_잘못_등록한_반려동물을_지운다():
    stub = _StubUseCase()
    assert (await _delete(stub, STAFF)).status_code == 204
    assert stub.commands[0].pet_id == 101


async def test_마지막_반려동물이면_409_LAST_PET_이다():
    response = await _delete(_StubUseCase(LastPetError("마지막")), STAFF)
    assert (response.status_code, response.json()["code"]) == (409, "LAST_PET")


async def test_customer_write_가_없으면_403_이다():
    response = await _delete(_StubUseCase(), NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
