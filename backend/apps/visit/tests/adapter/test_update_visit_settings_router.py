from datetime import time

from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.dependencies.update_visit_settings_provider import get_update_visit_settings_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

SETTINGS = VisitSettingsView(opens_at=time(10), closes_at=time(19), default_duration_minutes=120,
                             closed_weekdays=[0])
BODY = {"opens_at": "09:30", "closes_at": "18:00", "default_duration_minutes": 90, "closed_weekdays": [0, 6]}


async def test_사장은_설정을_바꾼다():
    stub = Recorder(SETTINGS)
    async with client(build_app(update_visit_settings_router, get_update_visit_settings_use_case, stub)) as c:
        response = await c.put("/v1/shops/3/visit-settings", json=BODY)
    assert response.status_code == 200
    settings = stub.calls[0].settings
    assert (settings.opens_at, settings.closes_at, settings.default_duration_minutes, settings.closed_weekdays) == (
        time(9, 30), time(18), 90, frozenset({0, 6}))


async def test_직원은_설정을_바꾸지_못한다():
    """V8 — 일정·메뉴 수정은 shop:update(사장만)."""
    async with client(build_app(update_visit_settings_router, get_update_visit_settings_use_case,
                                Recorder(SETTINGS), STAFF)) as c:
        response = await c.put("/v1/shops/3/visit-settings", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED")


async def test_요일이_범위를_벗어나거나_문자열이면_422_다():
    async with client(build_app(update_visit_settings_router, get_update_visit_settings_use_case,
                                Recorder(SETTINGS))) as c:
        for bad in ({**BODY, "closed_weekdays": [7]}, {**BODY, "closed_weekdays": ["0"]},
                    {**BODY, "default_duration_minutes": "90"}, {**BODY, "opens_at": "10:00+09:00"}):
            assert error_of(await c.put("/v1/shops/3/visit-settings", json=bad)) == (422, "VALIDATION_ERROR")
