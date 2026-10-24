from notification.adapter.inbound.api.v1.notification_myself_router import notification_myself_router
from notification.app.dtos.notification_myself_dto import NotificationMyselfResponse
from notification.dependencies.notification_myself_provider import get_notification_myself_use_case
from notification.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_멤버는_자기소개를_본다():
    stub = Recorder(NotificationMyselfResponse(id=7, name="알림 (notification)", introduction="소개"))
    async with client(build_app(notification_myself_router, get_notification_myself_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/notification/myself")
    assert response.json() == {"id": 7, "name": "알림 (notification)", "introduction": "소개"}
    assert stub.calls[0].id == 7
