from datetime import time

from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.dependencies.get_visit_settings_provider import get_get_visit_settings_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client

SETTINGS = VisitSettingsView(opens_at=time(10), closes_at=time(19), default_duration_minutes=120,
                             closed_weekdays=[0])


async def test_직원도_설정을_본다():
    stub = Recorder(SETTINGS)
    async with client(build_app(get_visit_settings_router, get_get_visit_settings_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visit-settings")
    assert response.json() == {"opens_at": "10:00:00", "closes_at": "19:00:00",
                               "default_duration_minutes": 120, "closed_weekdays": [0]}
    assert stub.calls[0].ctx.shop_id == 3
