from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from notification.app.dtos.link_channel_dto import LinkChannelCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.app.ports.input.link_channel_use_case import LinkChannelUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.overview import load_overview
from notification.app.services.template_registration import register_template
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.domain.services.templates import TEXT_VERSION
from notification.domain.value_objects.channel_status import LINKED, TOKEN_REQUESTED
from notification.domain.value_objects.message_kind import DEFAULT_KINDS


class LinkChannelInteractor(LinkChannelUseCase):
    """6자리 토큰으로 채널을 연동한다(설계 6.2-2). 같은 요청에서 설정 기본값을 만들고 기본 5종 템플릿을 등록·검수 요청한다.

    업체 호출(연동·템플릿 등록)을 전부 마친 뒤에 저장한다 — 잠금을 쥔 채 업체를 부르지 않는다(N14). 템플릿 등록 하나가
    업체 오류로 실패하면 그 종류만 빠지고 디스패처의 10분 주기가 다시 등록한다(설계 9.5). 틀린 토큰은 TokenInvalidError
    그대로(400) — 시도는 맞든 틀리든 센다(N4).
    """

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

    async def link_channel(self, command: LinkChannelCommand) -> NotificationOverviewView:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is not None and channel.is_linked:
            raise ChannelAlreadyLinkedError("이미 연동된 채널입니다.")
        if channel is None or channel.status != TOKEN_REQUESTED:
            raise ChannelNotLinkedError("먼저 인증번호를 받아 주세요.")
        if not await self._limiter.allow(ctx.shop_id, "link"):
            raise TooManyNotificationRequestsError("인증번호 입력이 너무 잦습니다. 토큰을 다시 받아 주세요.")
        try:
            provider_channel_id = await self._gateway.link_channel(
                command.search_id, command.admin_phone, command.category_code, command.token)
        except GatewayError as exc:
            raise ProviderUnavailableError("발송 업체에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from exc
        registered = {}
        for kind in DEFAULT_KINDS:
            template_id = await register_template(self._gateway, provider_channel_id, kind)
            if template_id is not None:
                registered[kind] = template_id

        now = self._now()
        await self._channels.save(ctx, replace(channel, status=LINKED, provider_channel_id=provider_channel_id,
                                               linked_at=now))
        await self._settings.ensure(ctx)
        for kind, template_id in registered.items():
            await self._templates.upsert(ctx, kind, TEXT_VERSION, template_id, now)
        return await load_overview(ctx, self._channels, self._settings, self._templates)
