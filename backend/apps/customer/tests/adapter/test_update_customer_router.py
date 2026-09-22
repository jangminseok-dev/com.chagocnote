from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
from customer.dependencies.update_customer_provider import get_update_customer_use_case
from customer.tests.helpers.api import CUSTOMER_BODY, NO_WRITE, STAFF, build_app, customer_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def update_customer(self, command):
        self.commands.append(command)
        return customer_detail_view()


async def _put(stub, body, access):
    app = build_app(update_customer_router, get_update_customer_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.put("/v1/shops/3/customers/1", json=body)


async def test_직원도_보호자를_고친다():
    stub = _StubUseCase()
    response = await _put(stub, CUSTOMER_BODY, STAFF)
    assert response.status_code == 200
    command = stub.commands[0]
    assert (command.customer_id, command.customer.name, command.customer.marketing_consent) == (1, "김민지", True)


async def test_customer_write_가_없으면_403_이다():
    stub = _StubUseCase()
    response = await _put(stub, CUSTOMER_BODY, NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []
