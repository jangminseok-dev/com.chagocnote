import pytest

from notification.adapter.inbound.api.v1.request_channel_token_router import request_channel_token_router
from notification.dependencies.request_channel_token_provider import get_request_channel_token_use_case
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

BODY = {"search_id": "hisshaus", "admin_phone": "01012345678", "category_code": "003001"}


def _without(key: str) -> dict:
    return {k: v for k, v in BODY.items() if k != key}


def _app(stub, access=None):
    return build_app(request_channel_token_router, get_request_channel_token_use_case, stub, access)


async def test_사장은_토큰을_신청한다_202():
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.post("/v1/shops/3/notification/channel/token", json=BODY)
    assert (response.status_code, response.json()) == (202, {"status": "token_requested"})
    [command] = stub.calls
    assert (command.ctx.shop_id, command.search_id, command.admin_phone, command.category_code) == (
        3, "hisshaus", "01012345678", "003001")


async def test_직원은_신청하지_못한다():
    """N18"""
    stub = Recorder(None)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/notification/channel/token", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, "search_id": v} for v in ("", "a" * 101, "a b", "a\x00b", 12, None)),
    *({**BODY, "admin_phone": v} for v in ("010-1234-5678", "0212345678", "", "0101234567a", 1012345678, None)),
    *({**BODY, "category_code": v} for v in ("", "a" * 21, None)),
    _without("search_id"), _without("admin_phone"), _without("category_code"),
    {}, [], "문자열", None,
], ids=str)
async def test_빈_값_너무_긴_값_번호_형식_빠진_칸은_422_다(bad):
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.post("/v1/shops/3/notification/channel/token", json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


@pytest.mark.parametrize("error, expected", [
    (ChannelAlreadyLinkedError("이미 연동"), (409, "NOTIFICATION_CHANNEL_LINKED")),
    (TooManyNotificationRequestsError("너무 잦음"), (429, "NOTIFICATION_RATE_LIMITED")),
    (ProviderUnavailableError("업체 오류"), (502, "NOTIFICATION_PROVIDER_UNAVAILABLE")),
])
async def test_도메인_오류는_표의_상태로_나간다(error, expected):
    async with client(_app(Recorder(error=error))) as c:
        response = await c.post("/v1/shops/3/notification/channel/token", json=BODY)
    assert error_of(response) == expected
