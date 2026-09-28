import pytest

from visit.adapter.inbound.api.v1.update_report_settings_router import update_report_settings_router
from visit.dependencies.update_report_settings_provider import get_update_report_settings_use_case
from visit.domain.value_objects.report_settings import ReportSettings
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

BODY = {"link_days": 7, "show_menus": False, "show_shop_info": True, "show_weight": True, "show_amount": False}
FLAGS = ("show_menus", "show_shop_info", "show_weight", "show_amount")


def _without(key: str) -> dict:
    return {k: v for k, v in BODY.items() if k != key}


def _app(stub, access=None):
    return build_app(update_report_settings_router, get_update_report_settings_use_case, stub, access)


@pytest.mark.parametrize("link_days", [7, 30, None])
async def test_사장은_알림장_설정을_바꾼다(link_days):
    saved = ReportSettings(**{**BODY, "link_days": link_days})
    stub = Recorder(saved)
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/report-settings", json={**BODY, "link_days": link_days})
    assert (response.status_code, response.json()) == (200, {**BODY, "link_days": link_days})
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].settings) == (3, saved)


async def test_직원은_알림장_설정을_바꾸지_못한다():
    """R16 — 알림장 설정은 shop:update(사장만)."""
    stub = Recorder(ReportSettings(**BODY))
    async with client(_app(stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/report-settings", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED")
    assert stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, "link_days": days} for days in (0, 1, 8, 31, -7, 365, "30", "7", 30.5, True, [30])),
    _without("link_days"),
    *({**BODY, flag: value} for flag in FLAGS for value in ("true", 1, 0, None)),
    *(_without(flag) for flag in FLAGS),
    [],
    [BODY],
    {},
    "문자열",
    None,
], ids=str)
async def test_고를_수_없는_기간과_불리언이_아닌_값과_빠진_칸은_422_다(bad):
    """R15"""
    stub = Recorder(ReportSettings(**BODY))
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/report-settings", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR")
    assert stub.calls == []
