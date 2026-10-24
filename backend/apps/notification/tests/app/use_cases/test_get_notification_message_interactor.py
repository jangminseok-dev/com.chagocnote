"""줄 하나의 상태(알림장 보내기 직후 폴링용) — 없거나 다른 매장이면 404. 실패 줄이면 share_text 가 함께 온다."""
import pytest

from notification.app.dtos.get_notification_message_dto import GetNotificationMessageQuery
from notification.domain.errors import MessageNotFoundError
from notification.domain.value_objects.message_status import ACCEPTED, FAILED
from notification.tests.helpers.builders import ctx, kst, message
from notification.tests.helpers.message_world import MessageWorld

VARIABLES = {"starts_at": kst(10, 16, 14).isoformat()}


async def test_있으면_줄을_돌려주고_실패_줄에만_share_text_가_있다():
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, status=ACCEPTED, variables=VARIABLES)
    world.messages.rows[2] = message(id=2, status=FAILED, variables=VARIABLES)

    accepted = await world.get.get_notification_message(GetNotificationMessageQuery(ctx=ctx(), message_id=1))
    failed = await world.get.get_notification_message(GetNotificationMessageQuery(ctx=ctx(), message_id=2))

    assert (accepted.message.id, accepted.share_text) == (1, None)
    assert (failed.message.id, failed.share_text) == (2, "[두부네] 10월 16일(금) 14:00 예약이 접수되었어요.")


@pytest.mark.parametrize("message_id, shop_id", [(9, 1), (1, 2)], ids=["없는 줄", "다른 매장"])
async def test_없거나_다른_매장의_줄이면_404_다(message_id, shop_id):
    """N1"""
    world = MessageWorld()
    world.messages.rows[1] = message(id=1, status=FAILED, variables=VARIABLES)

    with pytest.raises(MessageNotFoundError):
        await world.get.get_notification_message(GetNotificationMessageQuery(ctx=ctx(shop_id=shop_id),
                                                                             message_id=message_id))
