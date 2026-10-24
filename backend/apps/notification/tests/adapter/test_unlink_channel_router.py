from notification.adapter.inbound.api.v1.unlink_channel_router import unlink_channel_router
from notification.dependencies.unlink_channel_provider import get_unlink_channel_use_case
from notification.domain.errors import ChannelNotLinkedError
from notification.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


def _app(stub, access=None):
    return build_app(unlink_channel_router, get_unlink_channel_use_case, stub, access)


async def test_사장은_연동을_해제한다_204():
    stub = Recorder(None)
    async with client(_app(stub)) as c:
        response = await c.delete("/v1/shops/3/notification/channel")
    assert (response.status_code, response.content) == (204, b"")
    assert stub.calls[0].ctx.shop_id == 3


async def test_직원은_해제하지_못한다():
    stub = Recorder(None)
    async with client(_app(stub, STAFF)) as c:
        response = await c.delete("/v1/shops/3/notification/channel")
    assert error_of(response) == (403, "PERMISSION_DENIED") and stub.calls == []


async def test_연동되지_않았으면_409_다():
    async with client(_app(Recorder(error=ChannelNotLinkedError("연동 전")))) as c:
        response = await c.delete("/v1/shops/3/notification/channel")
    assert error_of(response) == (409, "NOTIFICATION_CHANNEL_NOT_LINKED")
