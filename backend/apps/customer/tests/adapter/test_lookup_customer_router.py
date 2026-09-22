from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.lookup_customer_router import lookup_customer_router
from customer.app.dtos.lookup_customer_dto import LookupCustomerResult
from customer.dependencies.lookup_customer_provider import get_lookup_customer_use_case
from customer.domain.errors import CustomerNotFoundError
from customer.tests.helpers.api import NO_WRITE, build_app


class _StubUseCase:
    def __init__(self, found=True):
        self.found = found
        self.queries = []

    async def lookup_customer(self, query):
        self.queries.append(query)
        if not self.found:
            raise CustomerNotFoundError("이 번호로 등록된 고객이 없습니다.")
        return LookupCustomerResult(customer_id=1, name="김민지", pet_names=["콩이", "두부"])


async def _get(stub, path):
    app = build_app(lookup_customer_router, get_lookup_customer_use_case, stub, access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_멤버는_번호로_조회한다():
    stub = _StubUseCase()
    response = await _get(stub, "/v1/shops/3/customers/lookup?phone=010-1234-5678")
    assert response.json() == {"customer_id": 1, "name": "김민지", "pet_names": ["콩이", "두부"]}
    assert stub.queries[0].phone == "010-1234-5678"


async def test_없으면_404_CUSTOMER_NOT_FOUND_다():
    stub = _StubUseCase(found=False)
    response = await _get(stub, "/v1/shops/3/customers/lookup?phone=01012345678")
    assert (response.status_code, response.json()["code"]) == (404, "CUSTOMER_NOT_FOUND")


async def test_번호가_없으면_422_다():
    response = await _get(_StubUseCase(), "/v1/shops/3/customers/lookup")
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")
