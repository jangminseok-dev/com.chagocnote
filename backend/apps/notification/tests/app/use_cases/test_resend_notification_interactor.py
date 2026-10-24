"""다시 보내기 — 채널 linked·템플릿 approved 여야 하고 설정은 보지 않는다. 가장 최근 줄이 없으면 404, 대기 중이면 409,
끝난 줄(취소·성공·실패)이면 그 줄의 variables·pet_id 로 지금 보낼 새 줄을 만들고 디스패처를 깨운다."""
import pytest

from notification.app.dtos.resend_notification_dto import ResendNotificationCommand
from notification.domain.errors import (
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    TemplateNotApprovedError,
)
from notification.domain.value_objects.channel_status import UNLINKED
from notification.domain.value_objects.message_kind import CONFIRM, REMINDER
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    FAILED,
    FALLBACK_SENT,
    SCHEDULED,
    SENDING,
    SENT,
)
from notification.domain.value_objects.template_status import PENDING, REJECTED
from notification.tests.helpers.builders import channel, ctx, kst, message, settings, template
from notification.tests.helpers.message_world import NOW, MessageWorld

VARIABLES = {"starts_at": kst(10, 16, 14).isoformat()}
COMMAND = ResendNotificationCommand(ctx=ctx(member_id=11), visit_id=1, kind=CONFIRM)


def _failed(**overrides):
    fields = dict(id=1, status=FAILED, error_kind="permanent", error_code="3104", pet_id=101, variables=VARIABLES)
    fields.update(overrides)
    return message(**fields)


@pytest.mark.parametrize("status", [FAILED, SENT, FALLBACK_SENT, CANCELED])
async def test_끝난_줄이면_같은_재료로_지금_보낼_새_줄을_만들고_깨운다(status):
    world = MessageWorld()
    world.messages.rows[1] = _failed(status=status)

    message_id = await world.resend.resend_notification(COMMAND)

    created = world.messages.rows[message_id]
    assert message_id == 2
    assert (created.visit_id, created.customer_id, created.pet_id, created.kind, created.status) == (
        1, 1, 101, CONFIRM, SCHEDULED)
    assert (created.scheduled_at, created.variables, created.requested_by_member_id) == (NOW, VARIABLES, 11)
    assert world.journal[-2:] == [("create_message", 1, CONFIRM), ("wake",)]


async def test_설정이_꺼진_종류여도_매장이_직접_누른_것이니_보낸다():
    world = MessageWorld()
    world.settings.rows[1] = settings(confirm_enabled=False)
    world.messages.rows[1] = _failed(status=CANCELED, canceled_reason="setting_off")

    assert await world.resend.resend_notification(COMMAND) == 2


@pytest.mark.parametrize("status", [SCHEDULED, SENDING, ACCEPTED])
async def test_가장_최근_줄이_대기_중이면_409_이고_만들지_않는다(status):
    """N5"""
    world = MessageWorld()
    world.messages.rows[1] = _failed(id=1, created_at=kst(10, 14, 10))
    world.messages.rows[2] = _failed(id=2, status=status, created_at=kst(10, 14, 11))

    with pytest.raises(MessageAlreadyPendingError):
        await world.resend.resend_notification(COMMAND)
    assert len(world.messages.rows) == 2 and ("wake",) not in world.journal


async def test_가장_최근_줄의_재료를_쓴다():
    world = MessageWorld()
    old = {"starts_at": kst(10, 15, 14).isoformat()}
    world.messages.rows[1] = _failed(id=1, status=SENT, variables=old, created_at=kst(10, 14, 10))
    world.messages.rows[2] = _failed(id=2, status=FAILED, variables=VARIABLES, pet_id=None, created_at=kst(10, 14, 11))

    message_id = await world.resend.resend_notification(COMMAND)

    assert (world.messages.rows[message_id].variables, world.messages.rows[message_id].pet_id) == (VARIABLES, None)


@pytest.mark.parametrize("rows", [
    {}, {1: _failed(kind=REMINDER)}, {1: _failed(visit_id=2)}, {1: _failed(shop_id=2, visit_id=1)},
], ids=["줄 없음", "다른 종류", "다른 방문", "다른 매장"])
async def test_이_매장_방문_종류의_줄이_없으면_404_다(rows):
    """N1"""
    world = MessageWorld()
    world.messages.rows.update(rows)

    with pytest.raises(MessageNotFoundError):
        await world.resend.resend_notification(COMMAND)
    assert ("wake",) not in world.journal


@pytest.mark.parametrize("status", [None, UNLINKED])
async def test_채널이_linked_가_아니면_409_NOT_LINKED_다(status):
    world = MessageWorld()
    world.channels.rows.pop(1)
    if status is not None:
        world.channels.rows[1] = channel(status=status, unlinked_at=NOW)
    world.messages.rows[1] = _failed()

    with pytest.raises(ChannelNotLinkedError):
        await world.resend.resend_notification(COMMAND)


@pytest.mark.parametrize("break_world", [
    lambda w: w.templates.rows.pop((1, CONFIRM)),
    lambda w: w.templates.rows.__setitem__((1, CONFIRM), template(status=PENDING, decided_at=None)),
    lambda w: w.templates.rows.__setitem__((1, CONFIRM), template(status=REJECTED, rejected_reason="x")),
], ids=["템플릿 없음", "검수 중", "반려"])
async def test_템플릿이_approved_가_아니면_409_TEMPLATE_NOT_APPROVED_다(break_world):
    world = MessageWorld()
    break_world(world)
    world.messages.rows[1] = _failed()

    with pytest.raises(TemplateNotApprovedError):
        await world.resend.resend_notification(COMMAND)
    assert len(world.messages.rows) == 1
