from datetime import date

import pytest

from visit.adapter.inbound.api.v1.list_sales_visits_router import list_sales_visits_router
from visit.app.dtos.list_sales_visits_dto import SalesVisitItemView, SalesVisitsView
from visit.app.services.pet_cards import PetCard
from visit.dependencies.list_sales_visits_provider import get_list_sales_visits_use_case
from visit.domain.errors import VisitInputError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

VIEW = SalesVisitsView(
    items=[SalesVisitItemView(visit_id=9, date=date(2026, 11, 5), pet=PetCard(101, "두부", "t/51"), amount=None),
           SalesVisitItemView(visit_id=8, date=date(2026, 11, 4), pet=None, amount=30_000)],
    next_cursor="abc",
)
BASE = "/v1/shops/3/sales/visits"


def _app(stub, access=None):
    return build_app(list_sales_visits_router, get_list_sales_visits_use_case, stub, access)


async def test_사장은_방문_목록을_읽는다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.get(f"{BASE}?span=month&anchor=2026-11-14&filter=menu&menu_id=7&cursor=abc")
        await c.get(f"{BASE}?span=week&filter=no_show")
    assert (response.status_code, response.json()) == (200, {
        "items": [
            {"visit_id": 9, "date": "2026-11-05", "pet": {"pet_id": 101, "name": "두부", "photo_url": "t/51"},
             "amount": None},
            {"visit_id": 8, "date": "2026-11-04", "pet": None, "amount": 30_000},
        ],
        "next_cursor": "abc",
    })
    first, second = stub.calls
    assert (first.ctx.shop_id, first.span, first.anchor, first.filter, first.menu_id, first.cursor) == (
        3, "month", date(2026, 11, 14), "menu", 7, "abc")
    assert (second.span, second.anchor, second.filter, second.menu_id, second.cursor) == (
        "week", None, "no_show", None, None)


async def test_직원은_방문_목록을_보지_못한다():
    stub = Recorder(VIEW)
    async with client(_app(stub, STAFF)) as c:
        response = await c.get(f"{BASE}?span=month&filter=unrecorded")
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


@pytest.mark.parametrize("query", [
    "", "span=month", "filter=unrecorded", "span=month&filter=all", "span=quarter&filter=no_show",
    "span=month&filter=menu&menu_id=0", "span=month&filter=menu&menu_id=-1", "span=month&filter=menu&menu_id=x",
    "span=month&filter=menu&menu_id=9223372036854775808", "span=month&filter=menu&menu_id=1.5",
    "span=month&filter=no_show&anchor=2026-13-01", f"span=month&filter=no_show&cursor={'a' * 201}",
], ids=lambda q: q[:40] or "빈 질의")
async def test_없는_종류와_범위_밖의_값은_422_다(query):
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.get(f"{BASE}?{query}")
    assert error_of(response) == (422, "VALIDATION_ERROR")
    assert stub.calls == []


async def test_유스케이스가_입력을_거절하면_422_다():
    stub = Recorder(error=VisitInputError("어느 메뉴의 방문을 볼지 골라 주세요."))
    async with client(_app(stub)) as c:
        response = await c.get(f"{BASE}?span=month&filter=menu")
    assert error_of(response) == (422, "VALIDATION_ERROR")
