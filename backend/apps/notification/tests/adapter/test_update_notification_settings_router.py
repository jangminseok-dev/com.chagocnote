from datetime import time

import pytest

from notification.adapter.inbound.api.v1.update_notification_settings_router import (
    update_notification_settings_router,
)
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.dependencies.update_notification_settings_provider import (
    get_update_notification_settings_use_case,
)
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.errors import ChannelNotLinkedError, NotificationInputError, SenderNotVerifiedError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import channel, settings

BODY = {"confirm_enabled": True, "reminder_enabled": False, "report_enabled": True, "change_enabled": True,
        "next_visit_enabled": True, "reminder_time": "09:30", "next_visit_after_weeks": 6,
        "next_visit_cooldown_days": 45, "sms_fallback_enabled": False}
FLAGS = ("confirm_enabled", "reminder_enabled", "report_enabled", "change_enabled", "next_visit_enabled",
         "sms_fallback_enabled")
VIEW = NotificationOverviewView(channel=channel(), settings=settings(), templates=[])


def _without(key: str) -> dict:
    return {k: v for k, v in BODY.items() if k != key}


def _app(stub, access=None):
    return build_app(update_notification_settings_router, get_update_notification_settings_use_case, stub, access)


async def test_사장은_설정_전체를_바꾸고_overview_를_받는다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/notification/settings", json=BODY)
    assert response.status_code == 200 and response.json()["settings"]["reminder_time"] == "18:00"
    [command] = stub.calls
    assert command.ctx.shop_id == 3 and command.sms_fallback_enabled is False
    assert command.settings == NotificationSettings(
        confirm_enabled=True, reminder_enabled=False, report_enabled=True, change_enabled=True,
        next_visit_enabled=True, reminder_time=time(9, 30), next_visit_after_weeks=6, next_visit_cooldown_days=45)


async def test_주기를_비우면_None_이고_문자_대체를_켤_수_있다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        await c.put("/v1/shops/3/notification/settings",
                    json={**BODY, "next_visit_after_weeks": None, "sms_fallback_enabled": True})
    assert stub.calls[0].settings.next_visit_after_weeks is None and stub.calls[0].sms_fallback_enabled is True


async def test_직원은_설정을_바꾸지_못한다():
    """N18"""
    stub = Recorder(VIEW)
    async with client(_app(stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/notification/settings", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, flag: value} for flag in FLAGS for value in ("true", 1, 0, None)),
    *(_without(flag) for flag in FLAGS),
    *({**BODY, "reminder_time": v} for v in ("18:00:00", "25:00", "18:60", "9:00", "", "18시", None, 1800)),
    _without("reminder_time"),
    *({**BODY, "next_visit_after_weeks": v} for v in ("4", -1, 4.5, True)),
    _without("next_visit_after_weeks"),
    *({**BODY, "next_visit_cooldown_days": v} for v in ("30", -1, 30.5, None, True)),
    _without("next_visit_cooldown_days"),
    {}, [], "문자열", None,
], ids=str)
async def test_불리언_문자열_시각_형식_정수_아닌_값_빠진_칸은_422_다(bad):
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.put("/v1/shops/3/notification/settings", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (NotificationInputError("범위 밖"), (422, "VALIDATION_ERROR")),
    (SenderNotVerifiedError("인증 먼저"), (409, "NOTIFICATION_SENDER_NOT_VERIFIED")),
    (ChannelNotLinkedError("연동 먼저"), (409, "NOTIFICATION_CHANNEL_NOT_LINKED")),
])
async def test_도메인_오류는_표의_상태로_나간다(error, expected):
    async with client(_app(Recorder(error=error))) as c:
        response = await c.put("/v1/shops/3/notification/settings", json=BODY)
    assert error_of(response) == expected
