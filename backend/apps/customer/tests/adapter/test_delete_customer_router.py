from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.delete_customer_router import delete_customer_router
from customer.dependencies.delete_customer_provider import get_delete_customer_use_case
from customer.tests.helpers.api import STAFF, build_app


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def delete_customer(self, command):
        self.commands.append(command)


async def _delete(stub, access=None):
    app = build_app(delete_customer_router, get_delete_customer_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete("/v1/shops/3/customers/1")


async def test_사장은_고객을_삭제하고_204_를_받는다():
    stub = _StubUseCase()
    response = await _delete(stub)
    assert response.status_code == 204
    assert (stub.commands[0].ctx.shop_id, stub.commands[0].customer_id) == (3, 1)


async def test_직원은_고객을_삭제하지_못한다():
    stub = _StubUseCase()
    response = await _delete(stub, access=STAFF)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []
