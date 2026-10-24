import pytest

from notification.adapter.inbound.api.v1.link_channel_router import link_channel_router
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.dependencies.link_channel_provider import get_link_channel_use_case
from notification.domain.errors import ChannelNotLinkedError, TokenInvalidError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import channel, settings, template

BODY = {"search_id": "hisshaus", "admin_phone": "01012345678", "category_code": "003001", "token": "000000"}
VIEW = NotificationOverviewView(channel=channel(), settings=settings(), templates=[template(status="pending",
                                                                                            decided_at=None)])


def _app(stub, access=None):
    return build_app(link_channel_router, get_link_channel_use_case, stub, access)


async def test_사장은_토큰으로_연동하고_overview_를_받는다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.post("/v1/shops/3/notification/channel", json=BODY)
    body = response.json()
    assert response.status_code == 200
    assert (body["channel"]["status"], body["settings"]["reminder_time"], body["templates"][0]["status"]) == (
        "linked", "18:00", "pending")
    [command] = stub.calls
    assert (command.ctx.shop_id, command.search_id, command.admin_phone, command.category_code, command.token) == (
        3, "hisshaus", "01012345678", "003001", "000000")
    assert "KA01PF0001" not in response.text and "KA01TP0001" not in response.text


async def test_직원은_연동하지_못한다():
    stub = Recorder(VIEW)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/notification/channel", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, "token": v} for v in ("00000", "0000000", "abcdef", "00000a", "", 0, None)),
    {k: v for k, v in BODY.items() if k != "token"},
    {**BODY, "admin_phone": "010-1234-5678"},
    {**BODY, "search_id": ""},
], ids=str)
async def test_여섯_자리가_아닌_토큰과_잘못된_칸은_422_다(bad):
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.post("/v1/shops/3/notification/channel", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (TokenInvalidError("틀림"), (400, "NOTIFICATION_TOKEN_INVALID")),
    (ChannelNotLinkedError("먼저 인증번호를 받아 주세요"), (409, "NOTIFICATION_CHANNEL_NOT_LINKED")),
])
async def test_도메인_오류는_표의_상태로_나간다(error, expected):
    async with client(_app(Recorder(error=error))) as c:
        response = await c.post("/v1/shops/3/notification/channel", json=BODY)
    assert error_of(response) == expected
