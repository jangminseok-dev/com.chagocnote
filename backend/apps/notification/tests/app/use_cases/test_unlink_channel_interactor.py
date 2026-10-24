"""해제 — linked 에서만. unlinked·업체 ID 비움, 템플릿 삭제, 대기 줄 전부 channel_unlinked. 발신번호는 남는다."""
import pytest

from notification.app.dtos.unlink_channel_dto import UnlinkChannelCommand
from notification.domain.errors import ChannelNotLinkedError
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED, UNLINKED
from notification.domain.value_objects.message_kind import CONFIRM, REMINDER
from notification.domain.value_objects.message_status import CANCELED, SCHEDULED, SENT
from notification.tests.helpers.builders import channel, ctx, kst, message
from notification.tests.helpers.onboarding_world import NOW, OnboardingWorld

COMMAND = UnlinkChannelCommand(ctx=ctx())


async def test_해제하면_unlinked_가_되고_템플릿은_지우고_대기_줄은_channel_unlinked_로_취소한다():
    world = OnboardingWorld()
    world.channels.rows[1] = channel(sender_number="0212345678", sender_number_verified_at=kst(10, 5, 9),
                                     sms_fallback_enabled=True)
    world.messages.rows[1] = message(id=1, visit_id=1, kind=CONFIRM, status=SCHEDULED)
    world.messages.rows[2] = message(id=2, visit_id=1, kind=REMINDER, status=SCHEDULED)
    world.messages.rows[3] = message(id=3, visit_id=2, kind=CONFIRM, status=SENT)
    world.messages.rows[4] = message(id=4, shop_id=2, visit_id=9, kind=CONFIRM, status=SCHEDULED)

    await world.unlink.unlink_channel(COMMAND)

    saved = world.channels.rows[1]
    assert (saved.status, saved.unlinked_at, saved.provider_channel_id) == (UNLINKED, NOW, None)
    assert (saved.sender_number, saved.sender_number_verified_at, saved.sms_fallback_enabled) == (
        "0212345678", kst(10, 5, 9), True)
    assert world.template_ids() == []
    assert [(m.status, m.canceled_reason) for m in world.messages.rows.values()] == [
        (CANCELED, "channel_unlinked"), (CANCELED, "channel_unlinked"), (SENT, None), (SCHEDULED, None)]
    assert world.gateway.calls == []


@pytest.mark.parametrize("status", [None, TOKEN_REQUESTED, UNLINKED])
async def test_연동되지_않은_매장은_409_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status)
    with pytest.raises(ChannelNotLinkedError):
        await world.unlink.unlink_channel(COMMAND)
    assert ("delete_templates", 1) not in world.journal
