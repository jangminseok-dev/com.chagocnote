from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
from visit.app.dtos.list_visit_slots_dto import SlotView, VisitSlotsView
from visit.dependencies.list_visit_slots_provider import get_list_visit_slots_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

SLOTS = VisitSlotsView(
    date=date(2026, 10, 2), duration_minutes=90, closed_day=False,
    slots=[SlotView(starts_at=datetime(2026, 10, 2, 10, tzinfo=ZoneInfo("Asia/Seoul")), warnings=["overlap"])],
)


async def test_시간_칸_조회는_날짜_소요_시각_제외를_받는다():
    stub = Recorder(SLOTS)
    async with client(build_app(list_visit_slots_router, get_list_visit_slots_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/slots?date=2026-10-02&duration=90&at=14:10&exclude=7&exclude=8")
        plain = await c.get("/v1/shops/3/visits/slots?date=2026-10-02")
        bad = await c.get("/v1/shops/3/visits/slots?date=2026-10-02&exclude=0")
    assert response.json()["slots"] == [{"starts_at": "2026-10-02T10:00:00+09:00", "warnings": ["overlap"]}]
    query = stub.calls[0]
    assert (query.day, query.duration_minutes, query.at, query.exclude) == (date(2026, 10, 2), 90, time(14, 10), (7, 8))
    assert (stub.calls[1].duration_minutes, stub.calls[1].at, stub.calls[1].exclude) == (None, None, ())
    assert plain.status_code == 200
    assert error_of(bad) == (422, "VALIDATION_ERROR")
