from datetime import date

from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
from visit.app.dtos.schedule_view_dto import ClosedDateView
from visit.dependencies.list_closed_dates_provider import get_list_closed_dates_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_휴무_조회는_from_to_로_받는다():
    stub = Recorder([ClosedDateView(date=date(2026, 10, 9), note="한글날")])
    async with client(build_app(list_closed_dates_router, get_list_closed_dates_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/closed-dates?from=2026-10-01&to=2026-10-31")
    assert response.json() == {"items": [{"date": "2026-10-09", "note": "한글날"}]}
    assert (stub.calls[0].start, stub.calls[0].end) == (date(2026, 10, 1), date(2026, 10, 31))
