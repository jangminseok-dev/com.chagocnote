from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.list_customers_router import list_customers_router
from customer.app.dtos.list_customers_dto import CustomerListView, FamilyCardView, PetSummaryView
from customer.dependencies.list_customers_provider import get_list_customers_use_case
from customer.tests.helpers.api import NO_WRITE, build_app


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def list_customers(self, query):
        self.queries.append(query)
        pet = PetSummaryView(pet_id=101, name="콩이", species="dog", breed="말티즈", age_label="5살",
                             has_conditions=True, passed_away=False)
        card = FamilyCardView(customer_id=1, name="김민지", phone_masked="010-12··-5678", pets=[pet])
        return CustomerListView(items=[card], next_cursor="next", pet_count=1)


async def _get(stub, path):
    app = build_app(list_customers_router, get_list_customers_use_case, stub, access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_멤버는_기본값으로_목록을_본다():
    stub = _StubUseCase()
    response = await _get(stub, "/v1/shops/3/customers")
    assert response.status_code == 200
    body = response.json()
    assert (body["pet_count"], body["next_cursor"]) == (1, "next")
    assert body["items"][0]["phone_masked"] == "010-12··-5678"
    assert "phone" not in body["items"][0]   # 목록에는 전체 번호 칸이 없다
    query = stub.queries[0]
    assert (query.q, query.sort, query.include_passed, query.cursor) == (None, "recent", False, None)


async def test_검색어_정렬_포함_여부_커서를_넘긴다():
    stub = _StubUseCase()
    await _get(stub, "/v1/shops/3/customers?q=5678%20%EC%BD%A9&sort=name&include_passed=true&cursor=abc")
    query = stub.queries[0]
    assert (query.q, query.sort, query.include_passed, query.cursor) == ("5678 콩", "name", True, "abc")


async def test_모르는_정렬이나_너무_긴_검색어는_422_다():
    for path in ("/v1/shops/3/customers?sort=visit", "/v1/shops/3/customers?q=" + "가" * 51):
        response = await _get(_StubUseCase(), path)
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")
