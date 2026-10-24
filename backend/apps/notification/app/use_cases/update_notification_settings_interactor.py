from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.dtos.update_notification_settings_dto import UpdateNotificationSettingsCommand
from notification.app.ports.input.update_notification_settings_use_case import UpdateNotificationSettingsUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.overview import load_overview
from notification.app.services.template_registration import register_template
from notification.domain.errors import ChannelNotLinkedError, SenderNotVerifiedError
from notification.domain.services.schedule_rules import check_settings, next_visit_at, reminder_at
from notification.domain.services.templates import TEXT_VERSION
from notification.domain.value_objects.message_kind import KINDS, NEXT_VISIT, REMINDER


class UpdateNotificationSettingsInteractor(UpdateNotificationSettingsUseCase):
    """설정 전체 교체(설계 7.1). 저장한 뒤 후속 — ① 꺼진 종류의 대기 줄 취소(setting_off) ② reminder_time 이 바뀌면
    대기 중인 리마인드·다음 예약 제안의 시각 재계산(지난 리마인드는 too_late) ③ 다음 예약 제안을 처음 켜면 템플릿 등록
    ④ 채널의 문자 대체 칸.

    문자 대체는 발신번호 인증 뒤에만(N11 — DB CHECK 전에 409). 템플릿 등록(업체 호출)은 저장 전에 한다(N14).
    """

    def __init__(
        self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
        messages: MessageRepository, gateway: MessageGatewayPort, now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._messages = messages
        self._gateway = gateway
        self._now = now

    async def update_notification_settings(self, command: UpdateNotificationSettingsCommand) -> NotificationOverviewView:
        ctx, new = command.ctx, command.settings
        check_settings(new)
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("먼저 카카오톡 채널을 연동해 주세요.")
        if command.sms_fallback_enabled and channel.sender_number_verified_at is None:
            raise SenderNotVerifiedError("문자 대체를 켜려면 발신번호 인증을 먼저 해 주세요.")
        current = await self._settings.ensure(ctx)

        next_visit_template_id = None
        if new.next_visit_enabled and await self._templates.get(ctx, NEXT_VISIT) is None:
            next_visit_template_id = await register_template(self._gateway, channel.provider_channel_id, NEXT_VISIT)

        now = self._now()
        await self._settings.update(ctx, new)
        off = [kind for kind in KINDS if not new.enabled_for(kind)]
        if off:
            await self._messages.cancel_pending(ctx, "setting_off", kinds=off)
        if new.reminder_time != current.reminder_time:
            await self._reschedule(ctx, new.reminder_time, now)
        if next_visit_template_id is not None:
            await self._templates.upsert(ctx, NEXT_VISIT, TEXT_VERSION, next_visit_template_id, now)
        if command.sms_fallback_enabled != channel.sms_fallback_enabled:
            await self._channels.save(ctx, replace(channel, sms_fallback_enabled=command.sms_fallback_enabled))
        return await load_overview(ctx, self._channels, self._settings, self._templates)

    async def _reschedule(self, ctx, reminder_time, now: datetime) -> None:
        tz = ctx.timezone
        for m in await self._messages.list_pending(ctx, REMINDER):
            at = reminder_at(datetime.fromisoformat(m.variables["starts_at"]), reminder_time, tz, now)
            if at is None:
                await self._messages.cancel_pending(ctx, "too_late", visit_id=m.visit_id, kinds=(REMINDER,))
            else:
                await self._messages.save(ctx, replace(m, scheduled_at=at))
        for m in await self._messages.list_pending(ctx, NEXT_VISIT):
            at = next_visit_at(datetime.fromisoformat(m.variables["completed_at"]), int(m.variables["interval_weeks"]),
                               reminder_time, tz)
            await self._messages.save(ctx, replace(m, scheduled_at=at))
