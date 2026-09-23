from datetime import date

from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
from visit.app.dtos.get_visit_calendar_dto import CalendarDayView, VisitCalendarView
from visit.dependencies.get_visit_calendar_provider import get_get_visit_calendar_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

CALENDAR = VisitCalendarView(
    year=2026, month=9,
    days=[CalendarDayView(date=date(2026, 9, 1), visit_count=3, completed_count=1, open_count=2,
                          unresolved_count=1, closed_day=False)],
    unresolved_total=4, oldest_unresolved_date=date(2026, 7, 14),
)


async def test_달은_YYYY_MM_으로_받는다():
    stub = Recorder(CALENDAR)
    async with client(build_app(get_visit_calendar_router, get_get_visit_calendar_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/calendar?month=2026-09")
        for bad in ("2026-9", "2026-13", "202609", ""):
            assert error_of(await c.get(f"/v1/shops/3/visits/calendar?month={bad}")) == (422, "VALIDATION_ERROR")
    body = response.json()
    assert (body["month"], body["unresolved_total"], body["oldest_unresolved_date"]) == (
        "2026-09", 4, "2026-07-14")
    assert body["days"][0] == {"date": "2026-09-01", "visit_count": 3, "completed_count": 1, "open_count": 2,
                               "unresolved_count": 1, "closed_day": False}
    assert (stub.calls[0].year, stub.calls[0].month) == (2026, 9)
