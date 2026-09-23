from datetime import datetime
from zoneinfo import ZoneInfo

from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
from visit.app.dtos.get_visit_dto import PreviousVisitView, VisitDetailView
from visit.dependencies.get_visit_provider import get_get_visit_use_case
from visit.domain.errors import VisitNotFoundError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

DETAIL = VisitDetailView(
    visit=visit_view(1), group=[visit_view(2)],
    previous_visit=PreviousVisitView(visit_id=7, starts_at=datetime(2026, 9, 2, 14, tzinfo=ZoneInfo("Asia/Seoul"))),
    no_show_count=1,
)


async def test_직원도_방문_상세를_본다():
    stub = Recorder(DETAIL)
    async with client(build_app(get_visit_router, get_get_visit_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/1")
    body = response.json()
    assert (body["visit"]["visit_id"], [v["visit_id"] for v in body["group"]], body["no_show_count"]) == (1, [2], 1)
    assert body["previous_visit"] == {"visit_id": 7, "starts_at": "2026-09-02T14:00:00+09:00"}
    assert stub.calls[0].visit_id == 1


async def test_없는_방문은_404_범위를_넘는_ID_는_422_다():
    stub = Recorder(error=VisitNotFoundError("없음"))
    async with client(build_app(get_visit_router, get_get_visit_use_case, stub)) as c:
        assert error_of(await c.get("/v1/shops/3/visits/9")) == (404, "VISIT_NOT_FOUND")
        assert error_of(await c.get("/v1/shops/3/visits/9223372036854775808")) == (422, "VALIDATION_ERROR")
