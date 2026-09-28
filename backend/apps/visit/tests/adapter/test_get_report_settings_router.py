from visit.adapter.inbound.api.v1.get_report_settings_router import get_report_settings_router
from visit.dependencies.get_report_settings_provider import get_get_report_settings_use_case
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS
from visit.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_직원도_알림장_설정을_본다():
    stub = Recorder(DEFAULT_REPORT_SETTINGS)
    async with client(build_app(get_report_settings_router, get_get_report_settings_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/report-settings")
    assert response.status_code == 200
    assert response.json() == {"link_days": 30, "show_menus": True, "show_shop_info": True,
                               "show_weight": False, "show_amount": False}
    assert stub.calls[0].ctx.shop_id == 3
