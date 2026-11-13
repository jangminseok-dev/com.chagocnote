import pytest

from visit.adapter.inbound.api.v1.get_sales_goal_router import get_sales_goal_router
from visit.app.dtos.get_sales_goal_dto import SalesGoalView
from visit.dependencies.get_sales_goal_provider import get_get_sales_goal_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


def _app(stub, access=None):
    return build_app(get_sales_goal_router, get_get_sales_goal_use_case, stub, access)


@pytest.mark.parametrize("amount", [5_000_000, None])
async def test_사장은_월_목표를_읽는다(amount):
    stub = Recorder(SalesGoalView(monthly_amount=amount))
    async with client(_app(stub)) as c:
        response = await c.get("/v1/shops/3/sales/goal")
    assert (response.status_code, response.json()) == (200, {"monthly_amount": amount})
    assert stub.calls[0].ctx.shop_id == 3


async def test_직원은_월_목표를_읽지_못한다():
    """S1 — 매출은 sales:read(사장만)."""
    stub = Recorder(SalesGoalView(monthly_amount=5_000_000))
    async with client(_app(stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/sales/goal")
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert stub.calls == []
