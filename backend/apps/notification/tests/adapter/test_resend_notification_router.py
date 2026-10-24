"""다시 보내기 — reservation:write(직원도). 201 {message_id}. 종류는 여섯 중 하나여야 하고(422) 도메인 오류는 표대로."""
import pytest

from notification.adapter.inbound.api.v1.resend_notification_router import resend_notification_router
from notification.dependencies.resend_notification_provider import get_resend_notification_use_case
from notification.domain.errors import (
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    TemplateNotApprovedError,
)
from notification.domain.value_objects.message_kind import KINDS
from notification.tests.helpers.api import STAFF, Recorder, StubShopAccess, build_app, client, error_of

PATH = "/v1/shops/3/visits/12/notifications/confirm/resend"


def _app(stub, access=None):
    return build_app(resend_notification_router, get_resend_notification_use_case, stub, access)


@pytest.mark.parametrize("kind", KINDS)
async def test_직원도_다시_보내고_201_에_새_줄의_ID_를_받는다(kind):
    stub = Recorder(42)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post(f"/v1/shops/3/visits/12/notifications/{kind}/resend")
    assert (response.status_code, response.json()) == (201, {"message_id": 42})
    [command] = stub.calls
    assert (command.ctx.shop_id, command.ctx.member_id, command.visit_id, command.kind) == (3, 11, 12, kind)


async def test_예약_권한이_없는_멤버는_403_이다():
    """N2·설계 9.6"""
    stub = Recorder(42)
    async with client(_app(stub, StubShopAccess(frozenset({"record:write"}), role="staff"))) as c:
        response = await c.post(PATH)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("kind", ["CONFIRM", "sms", "confirm ", "confirm%0A", "0"])
async def test_없는_종류는_422_다(kind):
    stub = Recorder(42)
    async with client(_app(stub)) as c:
        response = await c.post(f"/v1/shops/3/visits/12/notifications/{kind}/resend")
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("visit_id", ["0", "9223372036854775808", "abc"])
async def test_방문_ID_가_범위_밖이거나_정수가_아니면_422_다(visit_id):
    stub = Recorder(42)
    async with client(_app(stub)) as c:
        response = await c.post(f"/v1/shops/3/visits/{visit_id}/notifications/confirm/resend")
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (ChannelNotLinkedError("연동 먼저"), (409, "NOTIFICATION_CHANNEL_NOT_LINKED")),
    (TemplateNotApprovedError("미승인"), (409, "NOTIFICATION_TEMPLATE_NOT_APPROVED")),
    (MessageNotFoundError("없음"), (404, "NOTIFICATION_MESSAGE_NOT_FOUND")),
    (MessageAlreadyPendingError("대기 중"), (409, "NOTIFICATION_ALREADY_PENDING")),
])
async def test_도메인_오류는_표의_상태로_나간다(error, expected):
    async with client(_app(Recorder(error=error))) as c:
        response = await c.post(PATH)
    assert error_of(response) == expected
