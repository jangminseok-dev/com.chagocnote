from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.get_customer_router import get_customer_router
from customer.dependencies.get_customer_provider import get_get_customer_use_case
from customer.app.dtos.customer_view_dto import CustomerOverviewView, UpcomingVisitView
from customer.domain.errors import (
    CustomerHasUpcomingVisitsError,
    CustomerInputError,
    CustomerNotFoundError,
    CustomerPhoneTakenError,
    LastPetError,
    PetHasUpcomingVisitsError,
    PetHasVisitsError,
    PetHealthConflictError,
    PetHealthRequiredError,
    PetNotFoundError,
    PetPassedAwayError,
)
from customer.tests.helpers.api import NOW, NO_WRITE, build_app, customer_detail_view


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.queries = []

    async def get_customer(self, query):
        self.queries.append(query)
        if self.error:
            raise self.error
        detail = customer_detail_view()
        return CustomerOverviewView(
            customer=detail.customer, pets=detail.pets, no_show_count=2,
            upcoming_visits=[UpcomingVisitView(visit_id=7, pet_id=101, pet_name="콩이", starts_at=NOW)],
            photos={101: "t/51"},
        )


async def _get(stub, path="/v1/shops/3/customers/1"):
    app = build_app(get_customer_router, get_get_customer_use_case, stub, access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_멤버는_전체_번호가_든_고객_상세를_본다():
    stub = _StubUseCase()
    response = await _get(stub)
    assert response.status_code == 200
    assert response.json()["customer"]["phone"] == "01012345678"
    assert response.json()["no_show_count"] == 2
    assert response.json()["upcoming_visits"] == [
        {"visit_id": 7, "pet_id": 101, "pet_name": "콩이", "starts_at": "2026-09-22T01:00:00Z"}]
    assert [(p["pet_id"], p["photo"]) for p in response.json()["pets"]] == [(101, "t/51")]
    assert (stub.queries[0].ctx.shop_id, stub.queries[0].customer_id) == (3, 1)


async def test_범위를_벗어난_ID_는_DB_에_닿기_전에_422_다():
    for path in ("/v1/shops/3/customers/0", "/v1/shops/3/customers/9223372036854775808",
                 "/v1/shops/3/customers/abc"):
        stub = _StubUseCase()
        response = await _get(stub, path)
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR"), path
        assert stub.queries == []


async def test_도메인_오류는_설계의_상태_코드와_코드로_나간다():
    cases = [
        (CustomerNotFoundError("x"), 404, "CUSTOMER_NOT_FOUND"),
        (PetNotFoundError("x"), 404, "PET_NOT_FOUND"),
        (CustomerPhoneTakenError("x"), 409, "CUSTOMER_PHONE_TAKEN"),
        (LastPetError("x"), 409, "LAST_PET"),
        (CustomerInputError("x"), 422, "VALIDATION_ERROR"),
        (PetHealthRequiredError("x"), 422, "PET_HEALTH_REQUIRED"),
        (PetHealthConflictError("x"), 422, "PET_HEALTH_CONFLICT"),
        (PetHasVisitsError("x"), 409, "PET_HAS_VISITS"),
        (PetHasUpcomingVisitsError("x"), 409, "PET_HAS_UPCOMING_VISITS"),
        (CustomerHasUpcomingVisitsError("x"), 409, "CUSTOMER_HAS_UPCOMING_VISITS"),
        (PetPassedAwayError("x"), 422, "PET_PASSED_AWAY"),
    ]
    for error, status, code in cases:
        response = await _get(_StubUseCase(error))
        assert (response.status_code, response.json()["code"]) == (status, code)
