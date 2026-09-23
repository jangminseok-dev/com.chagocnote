from visit.adapter.inbound.api.v1.get_visit_defaults_router import get_visit_defaults_router
from visit.app.dtos.get_visit_defaults_dto import VisitDefaultsView
from visit.app.dtos.visit_view_dto import MenuBriefView
from visit.dependencies.get_visit_defaults_provider import get_get_visit_defaults_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

DEFAULTS = VisitDefaultsView(source_visit_id=7, duration_minutes=150, menus=[MenuBriefView(menu_id=4, name="전체 미용")])


async def test_지난번처럼_채울_값을_준다():
    stub = Recorder(DEFAULTS)
    async with client(build_app(get_visit_defaults_router, get_get_visit_defaults_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/defaults?pet_id=101")
        assert error_of(await c.get("/v1/shops/3/visits/defaults")) == (422, "VALIDATION_ERROR")
    assert response.json() == {"source_visit_id": 7, "duration_minutes": 150,
                               "menus": [{"menu_id": 4, "name": "전체 미용"}]}
    assert stub.calls[0].pet_id == 101
