import pytest

from visit.adapter.inbound.api.v1.update_sales_goal_router import update_sales_goal_router
from visit.app.dtos.get_sales_goal_dto import SalesGoalView
from visit.dependencies.update_sales_goal_provider import get_update_sales_goal_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


def _app(stub, access=None):
    return build_app(update_sales_goal_router, get_update_sales_goal_use_case, stub, access)


@pytest.mark.parametrize("amount", [1, 5_000_000, 100_000_000, 0, None])
async def test_사장은_월_목표를_정한다(amount):
    stub = Recorder(SalesGoalView(monthly_amount=amount or None))
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/sales/goal", json={"monthly_amount": amount})
    assert (response.status_code, response.json()) == (200, {"monthly_amount": amount or None})
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].monthly_amount) == (3, amount)


async def test_직원은_월_목표를_정하지_못한다():
    """S1"""
    stub = Recorder(SalesGoalView(monthly_amount=5_000_000))
    async with client(_app(stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/sales/goal", json={"monthly_amount": 5_000_000})
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


@pytest.mark.parametrize("bad", [
    *({"monthly_amount": value} for value in (-1, 100_000_001, 1.5, "5", "5000000", True, False, [1], {})),
    {},
    {"amount": 5_000_000},
    [],
    "문자열",
    None,
], ids=str)
async def test_범위_밖과_숫자가_아닌_값과_빠진_칸은_422_다(bad):
    stub = Recorder(SalesGoalView(monthly_amount=None))
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/sales/goal", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR")
    assert stub.calls == []
