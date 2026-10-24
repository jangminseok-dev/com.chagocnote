from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from notification.app.dtos.confirm_sender_dto import ConfirmSenderCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.ports.input.confirm_sender_use_case import ConfirmSenderUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.overview import load_overview
from notification.domain.errors import (
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)


class ConfirmSenderInteractor(ConfirmSenderUseCase):
    """인증번호를 확인하고 발신번호와 인증 시각을 적는다. 틀리면 TokenInvalidError 그대로(400), 시도는 맞든 틀리든 센다."""

    def __init__(
        self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
        gateway: MessageGatewayPort, limiter: OnboardingLimiterPort, now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._gateway = gateway
        self._limiter = limiter
        self._now = now

    async def confirm_sender(self, command: ConfirmSenderCommand) -> NotificationOverviewView:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("먼저 카카오톡 채널을 연동해 주세요.")
        if not await self._limiter.allow(ctx.shop_id, "sender_confirm"):
            raise TooManyNotificationRequestsError("인증번호 입력이 너무 잦습니다. 인증을 다시 요청해 주세요.")
        try:
            await self._gateway.confirm_sender_verification(command.phone, command.code)
        except GatewayError as exc:
            raise ProviderUnavailableError("발송 업체에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from exc
        await self._channels.save(ctx, replace(channel, sender_number=command.phone,
                                               sender_number_verified_at=self._now()))
        return await load_overview(ctx, self._channels, self._settings, self._templates)
