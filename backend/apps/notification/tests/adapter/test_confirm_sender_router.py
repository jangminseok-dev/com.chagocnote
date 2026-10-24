import pytest

from notification.adapter.inbound.api.v1.confirm_sender_router import confirm_sender_router
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.dependencies.confirm_sender_provider import get_confirm_sender_use_case
from notification.domain.errors import TokenInvalidError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from notification.tests.helpers.builders import channel, kst, settings

PATH = "/v1/shops/3/notification/sender"
BODY = {"phone": "0212345678", "code": "000000"}
VIEW = NotificationOverviewView(
    channel=channel(sender_number="0212345678", sender_number_verified_at=kst(10, 5, 9)), settings=settings(),
    templates=[])


def _app(stub, access=None):
    return build_app(confirm_sender_router, get_confirm_sender_use_case, stub, access)


async def test_사장은_인증번호로_발신번호를_확인하고_overview_를_받는다():
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.post(PATH, json=BODY)
    assert response.status_code == 200
    assert (response.json()["channel"]["sender_number"], response.json()["channel"]["sender_verified"]) == (
        "0212345678", True)
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].phone, stub.calls[0].code) == (3, "0212345678", "000000")


async def test_직원은_확인하지_못한다():
    stub = Recorder(VIEW)
    async with client(_app(stub, STAFF)) as c:
        response = await c.post(PATH, json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


@pytest.mark.parametrize("bad", [
    *({**BODY, "code": v} for v in ("00000", "0000000", "abcdef", "", 0, None)),
    *({**BODY, "phone": v} for v in ("12345678", "010-1234-5678", "")),
    {"phone": "0212345678"}, {"code": "000000"}, {}, None,
], ids=str)
async def test_여섯_자리가_아닌_인증번호와_잘못된_번호는_422_다(bad):
    stub = Recorder(VIEW)
    async with client(_app(stub)) as c:
        response = await c.post(PATH, json=bad)
    assert error_of(response) == (422, "VALIDATION_ERROR") and stub.calls == []


async def test_틀린_인증번호는_400_이다():
    async with client(_app(Recorder(error=TokenInvalidError("틀림")))) as c:
        response = await c.post(PATH, json=BODY)
    assert error_of(response) == (400, "NOTIFICATION_TOKEN_INVALID")
