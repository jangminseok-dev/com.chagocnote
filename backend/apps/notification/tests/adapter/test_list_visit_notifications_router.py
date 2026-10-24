"""방문별 발송 내역 — 소속이면 읽는다. 칸은 MessageItem 열 개뿐이고 variables·업체 ID·오류 코드·고객 ID 는 없다(N12)."""
import pytest

from notification.adapter.inbound.api.v1.list_visit_notifications_router import list_visit_notifications_router
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.dependencies.list_visit_notifications_provider import get_list_visit_notifications_use_case
from notification.domain.value_objects.message_kind import REPORT
from notification.domain.value_objects.message_status import FAILED, SENT
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import kst, message

URL = "https://a/" + "t" * 43
VARIABLES = {"starts_at": kst(10, 16, 14).isoformat(), "url": URL, "expires_at": ""}
FAILED_ITEM = {"message_id": 2, "kind": "report", "status": "failed", "channel_used": None,
               "scheduled_at": "2026-10-14T11:00:00+09:00", "sent_at": None, "error_kind": "permanent",
               "canceled_reason": None, "requested_by_member_id": None, "share_text": f"[두부네] 알림장 {URL}"}
SENT_ITEM = {"message_id": 1, "kind": "confirm", "status": "sent", "channel_used": "alimtalk",
             "scheduled_at": "2026-10-14T11:00:00+09:00", "sent_at": "2026-10-14T11:00:05+09:00", "error_kind": None,
             "canceled_reason": None, "requested_by_member_id": 11, "share_text": None}


def _views() -> list[NotificationMessageView]:
    failed = message(id=2, kind=REPORT, status=FAILED, error_kind="permanent", error_code="3104", pet_id=101,
                     customer_id=7, provider_message_id="M4V-0002", variables=VARIABLES)
    sent = message(id=1, status=SENT, channel_used="alimtalk", sent_at=kst(10, 14, 11, 0).replace(second=5),
                   provider_message_id="M4V-0001", requested_by_member_id=11, variables=VARIABLES)
    return [NotificationMessageView(message=failed, share_text=f"[두부네] 알림장 {URL}"),
            NotificationMessageView(message=sent, share_text=None)]


def _app(stub, access=None):
    return build_app(list_visit_notifications_router, get_list_visit_notifications_use_case, stub, access)


async def test_직원도_목록을_보고_시각은_매장_시간대이며_실패_줄에만_share_text_가_있다():
    stub = Recorder(_views())
    async with client(_app(stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/12/notifications")
    assert response.status_code == 200
    assert response.json() == {"items": [FAILED_ITEM, SENT_ITEM]}
    [query] = stub.calls
    assert (query.ctx.shop_id, query.visit_id) == (3, 12)


async def test_응답에_variables_업체_ID_오류_코드_고객_ID_칸이_없다():
    """N12 — share_text 의 주소는 실패 줄의 문안으로만 나간다."""
    async with client(_app(Recorder(_views()))) as c:
        text = (await c.get("/v1/shops/3/visits/12/notifications")).text
    assert text.count(URL) == 1
    for secret in ("variables", "provider_message_id", "M4V-", "error_code", "3104", "customer_id", "pet_id",
                   "starts_at", "expires_at"):
        assert secret not in text, secret


async def test_빈_목록이면_items_가_빈다():
    async with client(_app(Recorder([]))) as c:
        response = await c.get("/v1/shops/3/visits/12/notifications")
    assert (response.status_code, response.json()) == (200, {"items": []})


@pytest.mark.parametrize("visit_id", ["0", "-1", "9223372036854775808", "abc", "1.5"])
async def test_방문_ID_가_범위_밖이거나_정수가_아니면_422_다(visit_id):
    stub = Recorder([])
    async with client(_app(stub)) as c:
        response = await c.get(f"/v1/shops/3/visits/{visit_id}/notifications")
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []
