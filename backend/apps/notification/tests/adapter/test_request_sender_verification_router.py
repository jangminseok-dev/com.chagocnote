import pytest

from notification.adapter.inbound.api.v1.request_sender_verification_router import (
    request_sender_verification_router,
)
from notification.dependencies.request_sender_verification_provider import (
    get_request_sender_verification_use_case,
)
from notification.domain.errors import TooManyNotificationRequestsError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

PATH = "/v1/shops/3/notification/sender/verification"


def _app(stub, access=None):
    return build_app(request_sender_verification_router, get_request_sender_verification_use_case, stub, access)


@pytest.mark.parametrize("phone", ["0212345678", "01012345678", "021234567"])
async def test_사장은_휴대폰이든_유선이든_발신번호_인증을_시작한다_202(phone):
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.post(PATH, json={"phone": phone})
    assert (response.status_code, response.json()) == (202, {"status": "verification_requested"})
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].phone) == (3, phone)


async def test_직원은_시작하지_못한다():
    stub = Recorder(None)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post(PATH, json={"phone": "0212345678"})
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({"phone": v} for v in ("12345678", "010123456789", "010-1234-5678", "", "0212345678a", 212345678, None)),
    {}, [], None,
], ids=str)
async def test_8자리_12자리_하이픈_빈_값은_422_다(bad):
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.post(PATH, json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


async def test_횟수_제한은_429_다():
    async with client(_app(Recorder(error=TooManyNotificationRequestsError("너무 잦음")))) as c:
        response = await c.post(PATH, json={"phone": "0212345678"})
    assert error_of(response) == (429, "NOTIFICATION_RATE_LIMITED")
