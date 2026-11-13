from datetime import date

import pytest

from visit.adapter.inbound.api.v1.get_sales_summary_router import get_sales_summary_router
from visit.app.dtos.get_sales_summary_dto import (
    BookingsView,
    BucketView,
    CompareView,
    CompareWindowView,
    GoalView,
    MenuView,
    PaymentView,
    PeriodView,
    PetsView,
    RegularView,
    ReportView,
    SalesSummaryView,
)
from visit.app.services.pet_cards import PetCard
from visit.dependencies.get_sales_summary_provider import get_get_sales_summary_use_case
from visit.domain.errors import VisitInputError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

DUBU = PetCard(pet_id=101, name="두부", photo_url="t/51")
SUMMARY = SalesSummaryView(
    span="month",
    period=PeriodView(start=date(2026, 11, 1), end=date(2026, 11, 30), elapsed_end=date(2026, 11, 14)),
    revenue=80_000, visit_count=3, priced_count=2, average=40_000,
    compare=CompareView(previous=CompareWindowView(date(2026, 10, 1), date(2026, 10, 14), 50_000), year_ago=None),
    goal=GoalView(monthly_amount=5_000_000),
    pets=PetsView(count=2, new_count=1, returning_count=1, faces=[DUBU], new=[], returning=[DUBU]),
    buckets=[BucketView(key="2026-11-01", revenue=80_000, visit_count=3, future=False, pets=[DUBU])],
    payments=[PaymentView(method="card", amount=30_000), PaymentView(method="none", amount=50_000)],
    menus=[MenuView(menu_id=7, name="전체 미용", amount=75_000, count=2, pet=DUBU),
           MenuView(menu_id=None, name="조정", amount=5_000, count=0, pet=None)],
    regulars=[RegularView(pet=DUBU, visit_count=4)],
    bookings=BookingsView(remaining=12, expected_amount=840_000, no_show=2, canceled=3),
    weekdays=[0, 0, 0, 0, 0, 0, 80_000],
    report=ReportView(completed=3, sent=2, opened=1),
    unrecorded_count=1, due_pet_count=7,
)
DUBU_JSON = {"pet_id": 101, "name": "두부", "photo_url": "t/51"}


def _app(stub, access=None):
    return build_app(get_sales_summary_router, get_get_sales_summary_use_case, stub, access)


async def test_사장은_요약을_읽는다_칸은_하나하나_적은_그대로다():
    stub = Recorder(SUMMARY)
    async with client(_app(stub)) as c:
        response = await c.get("/v1/shops/3/sales/summary?span=month&anchor=2026-11-14")
    assert response.status_code == 200
    assert response.json() == {
        "span": "month",
        "period": {"start": "2026-11-01", "end": "2026-11-30", "elapsed_end": "2026-11-14"},
        "revenue": 80_000, "visit_count": 3, "priced_count": 2, "average": 40_000,
        "compare": {"previous": {"start": "2026-10-01", "end": "2026-10-14", "revenue": 50_000}, "year_ago": None},
        "goal": {"monthly_amount": 5_000_000},
        "pets": {"count": 2, "new_count": 1, "returning_count": 1, "faces": [DUBU_JSON], "new": [],
                 "returning": [DUBU_JSON]},
        "buckets": [{"key": "2026-11-01", "revenue": 80_000, "visit_count": 3, "future": False, "pets": [DUBU_JSON]}],
        "payments": [{"method": "card", "amount": 30_000}, {"method": "none", "amount": 50_000}],
        "menus": [{"menu_id": 7, "name": "전체 미용", "amount": 75_000, "count": 2, "pet": DUBU_JSON},
                  {"menu_id": None, "name": "조정", "amount": 5_000, "count": 0, "pet": None}],
        "regulars": [{"pet": DUBU_JSON, "visit_count": 4}],
        "bookings": {"remaining": 12, "expected_amount": 840_000, "no_show": 2, "canceled": 3},
        "weekdays": [0, 0, 0, 0, 0, 0, 80_000],
        "report": {"completed": 3, "sent": 2, "opened": 1},
        "unrecorded_count": 1, "due_pet_count": 7,
    }
    query = stub.calls[0]
    assert (query.ctx.shop_id, query.span, query.anchor) == (3, "month", date(2026, 11, 14))


@pytest.mark.parametrize("span", ["day", "week", "month", "year"])
async def test_기간_넷을_받고_anchor_가_없으면_None_으로_넘긴다(span):
    stub = Recorder(SUMMARY)
    async with client(_app(stub)) as c:
        response = await c.get(f"/v1/shops/3/sales/summary?span={span}")
    assert response.status_code == 200
    assert (stub.calls[0].span, stub.calls[0].anchor) == (span, None)


async def test_직원은_매출을_보지_못한다():
    """S1 — 매출은 sales:read(사장만)."""
    stub = Recorder(SUMMARY)
    async with client(_app(stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/sales/summary?span=month")
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


@pytest.mark.parametrize("query", [
    "", "span=", "span=quarter", "span=MONTH", "span=month&span=year&anchor=x",
    "span=month&anchor=2026-13-01", "span=month&anchor=2026-02-30", "span=month&anchor=x",
    "span=month&anchor=20261114", "span=month&anchor=", "span=month&anchor=2026-11-14T10:00:00",
], ids=lambda q: q or "빈 질의")
async def test_없는_기간과_날짜가_아닌_anchor_는_422_다(query):
    stub = Recorder(SUMMARY)
    async with client(_app(stub)) as c:
        response = await c.get(f"/v1/shops/3/sales/summary?{query}")
    assert error_of(response) == (422, "VALIDATION_ERROR")
    assert stub.calls == []


async def test_유스케이스가_범위_밖이라고_하면_422_다():
    stub = Recorder(error=VisitInputError("볼 수 있는 기간을 벗어난 날짜입니다."))
    async with client(_app(stub)) as c:
        response = await c.get("/v1/shops/3/sales/summary?span=month&anchor=1999-12-31")
    assert error_of(response) == (422, "VALIDATION_ERROR")
