"""설정 전체 교체 — linked 필요, 범위 검사, 문자 대체는 인증 뒤에만. 후속 ① 꺼진 종류 취소 ② 리마인드 시각 재계산
③ 다음 예약 제안 템플릿 등록 ④ 채널의 sms_fallback_enabled."""
from datetime import time, timezone

import pytest

from notification.app.dtos.update_notification_settings_dto import UpdateNotificationSettingsCommand
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.domain.errors import ChannelNotLinkedError, NotificationInputError, SenderNotVerifiedError
from notification.domain.services.templates import TEXT_VERSION
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER
from notification.domain.value_objects.message_status import CANCELED, SCHEDULED
from notification.domain.value_objects.template_status import PENDING
from notification.tests.helpers.builders import channel, ctx, kst, message, settings, template
from notification.tests.helpers.onboarding_world import NOW, OnboardingWorld


def _iso(at) -> str:
    return at.astimezone(timezone.utc).isoformat()


def _command(sms_fallback_enabled=False, **overrides) -> UpdateNotificationSettingsCommand:
    return UpdateNotificationSettingsCommand(ctx=ctx(), settings=settings(**overrides),
                                             sms_fallback_enabled=sms_fallback_enabled)


async def test_설정을_저장하고_overview_를_돌려준다():
    world = OnboardingWorld()
    view = await world.update_settings.update_notification_settings(_command(reminder_enabled=False))
    assert world.settings.rows[1].reminder_enabled is False
    assert view.settings.reminder_enabled is False and view.channel.status == "linked"


@pytest.mark.parametrize("status", [None, TOKEN_REQUESTED])
async def test_연동되지_않은_매장은_409_다(status):
    world = OnboardingWorld(linked=False)
    if status is not None:
        world.channels.rows[1] = channel(status=status)
    with pytest.raises(ChannelNotLinkedError):
        await world.update_settings.update_notification_settings(_command())


@pytest.mark.parametrize("overrides", [
    {"reminder_time": time(7, 59)}, {"reminder_time": time(21, 1)}, {"next_visit_after_weeks": 0},
    {"next_visit_after_weeks": 53}, {"next_visit_cooldown_days": 0}, {"next_visit_cooldown_days": 366},
])
async def test_범위_밖_값은_422_이고_저장하지_않는다(overrides):
    world = OnboardingWorld()
    with pytest.raises(NotificationInputError):
        await world.update_settings.update_notification_settings(_command(**overrides))
    assert ("update_settings", 1) not in world.journal


async def test_발신번호_인증_없이_문자_대체를_켜면_409_이고_아무것도_바꾸지_않는다():
    """N11 — DB CHECK 에 닿기 전에 막는다."""
    world = OnboardingWorld()
    with pytest.raises(SenderNotVerifiedError):
        await world.update_settings.update_notification_settings(_command(sms_fallback_enabled=True))
    assert world.channels.rows[1].sms_fallback_enabled is False and ("update_settings", 1) not in world.journal


async def test_인증을_마쳤으면_문자_대체를_켜고_끌_수_있다():
    """④"""
    world = OnboardingWorld()
    world.channels.rows[1] = channel(sender_number="0212345678", sender_number_verified_at=kst(10, 5, 9))
    await world.update_settings.update_notification_settings(_command(sms_fallback_enabled=True))
    assert world.channels.rows[1].sms_fallback_enabled is True
    await world.update_settings.update_notification_settings(_command(sms_fallback_enabled=False))
    assert world.channels.rows[1].sms_fallback_enabled is False


async def test_끈_종류의_대기_줄은_setting_off_로_취소되고_변경을_끄면_change_와_cancel_둘이_취소된다():
    """①"""
    world = OnboardingWorld()
    world.messages.rows[1] = message(id=1, visit_id=1, kind=CONFIRM)
    world.messages.rows[2] = message(id=2, visit_id=1, kind=CHANGE)
    world.messages.rows[3] = message(id=3, visit_id=1, kind=CANCEL)
    world.messages.rows[4] = message(id=4, visit_id=1, kind=REMINDER)
    await world.update_settings.update_notification_settings(_command(change_enabled=False))
    assert [(m.kind, m.status, m.canceled_reason) for m in world.messages.rows.values()] == [
        (CONFIRM, SCHEDULED, None), (CHANGE, CANCELED, "setting_off"), (CANCEL, CANCELED, "setting_off"),
        (REMINDER, SCHEDULED, None)]


async def test_리마인드_시각을_바꾸면_대기_중인_reminder_와_next_visit_의_시각을_다시_계산한다():
    """② — 10월 16일 14시 예약의 리마인드는 15일 18시 → 15일 10시. 완료 10월 1일·4주의 제안은 29일 18시 → 29일 10시."""
    world = OnboardingWorld()
    world.settings.rows[1] = settings(next_visit_enabled=True)
    world.templates.rows[(1, NEXT_VISIT)] = template(id=6, kind=NEXT_VISIT, provider_template_id="KA01TP0006")
    world.messages.rows[1] = message(id=1, visit_id=1, kind=REMINDER, scheduled_at=kst(10, 15, 18),
                                     variables={"starts_at": _iso(kst(10, 16, 14))})
    world.messages.rows[2] = message(id=2, visit_id=2, kind=NEXT_VISIT, scheduled_at=kst(10, 29, 18),
                                     variables={"starts_at": _iso(kst(10, 1, 11)), "completed_at": _iso(kst(10, 1, 12)),
                                                "interval_weeks": "4"})
    await world.update_settings.update_notification_settings(
        _command(reminder_time=time(10, 0), next_visit_enabled=True))
    assert world.messages.rows[1].scheduled_at == kst(10, 15, 10)
    assert world.messages.rows[2].scheduled_at == kst(10, 29, 10)
    assert all(m.status == SCHEDULED for m in world.messages.rows.values())


async def test_새_리마인드_시각이_이미_지났으면_too_late_로_취소한다():
    """② — 지금이 14일 11시인데 14일 15시 예약의 리마인드를 13일 10시로 옮기면 이미 지났다."""
    world = OnboardingWorld()
    world.messages.rows[1] = message(id=1, visit_id=1, kind=REMINDER, scheduled_at=kst(10, 13, 18),
                                     variables={"starts_at": _iso(kst(10, 14, 15))})
    await world.update_settings.update_notification_settings(_command(reminder_time=time(10, 0)))
    assert (world.messages.rows[1].status, world.messages.rows[1].canceled_reason) == (CANCELED, "too_late")


async def test_리마인드_시각이_그대로면_대기_줄을_건드리지_않는다():
    world = OnboardingWorld()
    world.messages.rows[1] = message(id=1, visit_id=1, kind=REMINDER, scheduled_at=kst(10, 15, 18),
                                     variables={"starts_at": _iso(kst(10, 16, 14))})
    await world.update_settings.update_notification_settings(_command(confirm_enabled=False))
    assert world.messages.rows[1].scheduled_at == kst(10, 15, 18)
    assert not any(entry[0] == "save_message" for entry in world.journal)


async def test_다음_예약_제안을_처음_켜면_그_템플릿을_등록하고_이미_있으면_다시_등록하지_않는다():
    """③"""
    world = OnboardingWorld()
    await world.update_settings.update_notification_settings(_command(next_visit_enabled=True))
    registered = world.templates.rows[(1, NEXT_VISIT)]
    assert (registered.status, registered.provider_template_id, registered.requested_at) == (
        PENDING, f"tpl-KA01PF0001-{NEXT_VISIT}-v{TEXT_VERSION}", NOW)
    assert world.journal.count(("register_template", "KA01PF0001", NEXT_VISIT)) == 1

    await world.update_settings.update_notification_settings(_command(next_visit_enabled=True))
    assert world.journal.count(("register_template", "KA01PF0001", NEXT_VISIT)) == 1


async def test_다음_예약_제안_템플릿_등록이_실패해도_설정은_저장되고_템플릿만_없다():
    """③ — 디스패처의 10분 주기가 다시 등록한다(설계 9.5)."""
    world = OnboardingWorld()
    world.gateway.register_error = GatewayTransientError("timeout")
    view = await world.update_settings.update_notification_settings(_command(next_visit_enabled=True))
    assert world.settings.rows[1].next_visit_enabled is True
    assert (1, NEXT_VISIT) not in world.templates.rows and len(view.templates) == 5


async def test_템플릿_등록_호출은_저장_전에_한다_잠금을_쥔_채_부르지_않는다():
    world = OnboardingWorld()
    await world.update_settings.update_notification_settings(_command(next_visit_enabled=True))
    names = [entry[0] for entry in world.journal]
    assert names.index("register_template") < names.index("update_settings")


async def test_다음_예약_제안을_끄면_그_대기_줄은_취소되지만_템플릿은_남는다():
    world = OnboardingWorld()
    world.templates.rows[(1, NEXT_VISIT)] = template(id=6, kind=NEXT_VISIT, provider_template_id="KA01TP0006")
    world.settings.rows[1] = settings(next_visit_enabled=True)
    world.messages.rows[1] = message(id=1, visit_id=2, kind=NEXT_VISIT, scheduled_at=kst(10, 29, 18))
    await world.update_settings.update_notification_settings(_command(next_visit_enabled=False))
    assert (world.messages.rows[1].status, world.messages.rows[1].canceled_reason) == (CANCELED, "setting_off")
    assert (1, NEXT_VISIT) in world.templates.rows
