from visit.adapter.inbound.api.v1.get_visit_series_router import get_visit_series_router
from visit.app.dtos.get_visit_series_dto import VisitSeriesView
from visit.dependencies.get_visit_series_provider import get_get_visit_series_use_case
from visit.domain.errors import VisitSeriesNotFoundError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view


async def test_멤버가_묶음의_예약_목록을_읽는다():
    stub = Recorder(VisitSeriesView(id=7, interval_weeks=4, visits=[visit_view(3), visit_view(4)]))
    async with client(build_app(get_visit_series_router, get_get_visit_series_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visit-series/7")
    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["interval_weeks"], [v["visit_id"] for v in body["visits"]]) == (7, 4, [3, 4])
    assert (stub.calls[0].series_id, stub.calls[0].ctx.shop_id) == (7, 3)


async def test_없는_묶음은_404_와_잘못된_ID_는_422():
    stub = Recorder(error=VisitSeriesNotFoundError("없음"))
    async with client(build_app(get_visit_series_router, get_get_visit_series_use_case, stub, STAFF)) as c:
        assert error_of(await c.get("/v1/shops/3/visit-series/7")) == (404, "VISIT_SERIES_NOT_FOUND")
        assert (await c.get("/v1/shops/3/visit-series/0")).status_code == 422
