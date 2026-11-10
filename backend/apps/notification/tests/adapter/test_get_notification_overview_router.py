"""한눈에 보기 — 소속이면 읽는다. 시각은 매장 시간대, 업체 ID 는 내보내지 않는다(N12)."""
from notification.adapter.inbound.api.v1.get_notification_overview_router import get_notification_overview_router
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.dependencies.get_notification_overview_provider import get_get_notification_overview_use_case
from notification.domain.value_objects.template_status import REJECTED
from notification.tests.helpers.api import STAFF, Recorder, build_app, client
from notification.tests.helpers.builders import channel, kst, settings, template

CHANNEL = {"status": "linked", "linked_at": "2026-10-01T10:00:00+09:00", "sender_number": None,
           "sender_verified": False, "sms_fallback_enabled": False}
SETTINGS = {"confirm_enabled": True, "reminder_enabled": True, "report_enabled": True, "change_enabled": True,
            "next_visit_enabled": False, "reminder_time": "18:00", "next_visit_after_weeks": None,
            "next_visit_cooldown_days": 30}
TEMPLATES = [
    {"kind": "confirm", "status": "approved", "rejected_reason": None, "requested_at": "2026-10-01T10:00:00+09:00",
     "decided_at": "2026-10-02T10:00:00+09:00"},
    {"kind": "reminder", "status": "rejected", "rejected_reason": "변수 비중", "requested_at": "2026-10-01T10:00:00+09:00",
     "decided_at": "2026-10-02T10:00:00+09:00"},
]


def _app(view, access=None):
    return build_app(get_notification_overview_router, get_get_notification_overview_use_case, Recorder(view), access)


async def test_직원도_한눈에_보기를_보고_시각은_매장_시간대다():
    view = NotificationOverviewView(
        channel=channel(), settings=settings(),
        templates=[template(), template(id=2, kind="reminder", provider_template_id="KA01TP0002", status=REJECTED,
                                        rejected_reason="변수 비중")])
    async with client(_app(view, STAFF)) as c:
        response = await c.get("/v1/shops/3/notification")
    assert response.status_code == 200
    assert response.json() == {"channel": CHANNEL, "settings": SETTINGS, "templates": TEMPLATES}
    for secret in ("provider_channel_id", "provider_template_id", "KA01PF0001", "KA01TP0001"):
        assert secret not in response.text


async def test_연동_전엔_채널_none_설정_null_템플릿_빈_목록이다():
    async with client(_app(NotificationOverviewView(channel=None, settings=None, templates=[]))) as c:
        response = await c.get("/v1/shops/3/notification")
    assert response.json() == {
        "channel": {"status": "none", "linked_at": None, "sender_number": None, "sender_verified": False,
                    "sms_fallback_enabled": False},
        "settings": None, "templates": []}


async def test_발신번호를_인증했으면_번호와_인증_여부가_보인다():
    view = NotificationOverviewView(
        channel=channel(sender_number="0212345678", sender_number_verified_at=kst(10, 5, 9), sms_fallback_enabled=True),
        settings=settings(), templates=[])
    async with client(_app(view)) as c:
        body = (await c.get("/v1/shops/3/notification")).json()
    assert body["channel"] == {**CHANNEL, "sender_number": "0212345678", "sender_verified": True,
                               "sms_fallback_enabled": True}


async def test_overview_에_대기_칸은_나가지_않는다():
    waiting = template(pending_text_version=2, pending_provider_template_id="KA01TP0099")
    view = NotificationOverviewView(channel=channel(), settings=settings(), templates=[waiting])
    async with client(_app(view)) as c:
        response = await c.get("/v1/shops/3/notification")
    [item] = response.json()["templates"]
    assert set(item) == {"kind", "status", "rejected_reason", "requested_at", "decided_at"}
    assert item["status"] == "approved"
    assert "KA01TP0099" not in response.text and "pending_" not in response.text
