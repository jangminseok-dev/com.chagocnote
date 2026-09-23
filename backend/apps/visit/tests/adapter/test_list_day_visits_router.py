from datetime import date

from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_router
from visit.app.dtos.list_day_visits_dto import DayCountsView, DayVisitItemView, DayVisitsView
from visit.dependencies.list_day_visits_provider import get_list_day_visits_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

DAY = DayVisitsView(
    date=date(2026, 10, 2), closed_day=False,
    counts=DayCountsView(visit_count=1, reserved=1, in_progress=0, completed=0, canceled=0, no_show=0,
                         unresolved=0),
    items=[DayVisitItemView(visit=visit_view(), group_key="1:2026-10-02T05:00:00+00:00", overlapping=True,
                            unresolved=False)],
)


async def test_직원도_하루_목록을_본다():
    stub = Recorder(DAY)
    async with client(build_app(list_day_visits_router, get_list_day_visits_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits?date=2026-10-02")
        missing = await c.get("/v1/shops/3/visits")
    body = response.json()
    assert (body["date"], body["counts"]["visit_count"], body["items"][0]["overlapping"]) == (
        "2026-10-02", 1, True)
    assert body["items"][0]["visit"]["starts_at"] == "2026-10-02T14:00:00+09:00"
    assert stub.calls[0].day == date(2026, 10, 2)
    assert error_of(missing) == (422, "VALIDATION_ERROR")
