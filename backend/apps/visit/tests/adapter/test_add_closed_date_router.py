from datetime import date

from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_router
from visit.app.dtos.schedule_view_dto import ClosedDateView
from visit.dependencies.add_closed_date_provider import get_add_closed_date_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


async def test_휴무_추가는_사장만_메모의_빈_문자열은_None():
    stub = Recorder(ClosedDateView(date=date(2026, 10, 9), note=None))
    async with client(build_app(add_closed_date_router, get_add_closed_date_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/closed-dates", json={"date": "2026-10-09", "note": " "})
    assert response.status_code == 200
    assert (stub.calls[0].day, stub.calls[0].note) == (date(2026, 10, 9), None)
    async with client(build_app(add_closed_date_router, get_add_closed_date_use_case, stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/closed-dates", json={"date": "2026-10-09"})
    assert error_of(response) == (403, "PERMISSION_DENIED")
