from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.customer_myself_router import customer_myself_router
from customer.adapter.outbound.log_customer_myself_record_adapter import (
    LogCustomerMyselfRecordAdapter,
)
from customer.app.use_cases.customer_myself_interactor import CustomerMyselfInteractor
from customer.dependencies.customer_myself_provider import get_customer_myself_use_case
from customer.tests.helpers.api import NO_WRITE, build_app


async def _get(user_id=5):
    use_case = CustomerMyselfInteractor(record=LogCustomerMyselfRecordAdapter())
    app = build_app(customer_myself_router, get_customer_myself_use_case, use_case,
                    access=NO_WRITE, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/v1/shops/3/customers/myself")


async def test_멤버는_자기소개를_본다():
    response = await _get()
    assert response.status_code == 200
    assert response.json()["name"] == "고객 (customer)"
    assert "/customers/lookup" in response.json()["introduction"]


async def test_토큰이_없으면_401_이다():
    response = await _get(user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
