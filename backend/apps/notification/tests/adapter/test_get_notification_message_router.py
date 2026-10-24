"""줄 하나의 상태 — 소속이면 읽는다. 목록의 항목과 같은 MessageItem 이다. 없거나 다른 매장이면 404."""
import pytest

from notification.adapter.inbound.api.v1.get_notification_message_router import get_notification_message_router
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.dependencies.get_notification_message_provider import get_get_notification_message_use_case
from notification.domain.errors import MessageNotFoundError
from notification.domain.value_objects.message_status import ACCEPTED
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import kst, message

VARIABLES = {"starts_at": kst(10, 16, 14).isoformat()}
ITEM = {"message_id": 5, "kind": "confirm", "status": "accepted", "channel_used": None,
        "scheduled_at": "2026-10-14T11:00:00+09:00", "sent_at": None, "error_kind": None, "canceled_reason": None,
        "requested_by_member_id": None, "share_text": None}


def _app(stub, access=None):
    return build_app(get_notification_message_router, get_get_notification_message_use_case, stub, access)


async def test_직원도_줄_하나를_읽는다():
    view = NotificationMessageView(
        message=message(id=5, status=ACCEPTED, provider_message_id="M4V-0005", variables=VARIABLES), share_text=None)
    stub = Recorder(view)
    async with client(_app(stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/notifications/5")
    assert (response.status_code, response.json()) == (200, ITEM)
    assert "M4V-" not in response.text and "variables" not in response.text
    [query] = stub.calls
    assert (query.ctx.shop_id, query.message_id) == (3, 5)


async def test_없거나_다른_매장이면_404_다():
    """N1"""
    async with client(_app(Recorder(error=MessageNotFoundError("없음")))) as c:
        response = await c.get("/v1/shops/3/notifications/5")
    assert error_of(response) == (404, "NOTIFICATION_MESSAGE_NOT_FOUND")


@pytest.mark.parametrize("message_id", ["0", "9223372036854775808", "abc"])
async def test_메시지_ID_가_범위_밖이거나_정수가_아니면_422_다(message_id):
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.get(f"/v1/shops/3/notifications/{message_id}")
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []
