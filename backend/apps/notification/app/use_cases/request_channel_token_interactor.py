from __future__ import annotations

from dataclasses import replace

from notification.app.dtos.request_channel_token_dto import RequestChannelTokenCommand
from notification.app.ports.input.request_channel_token_use_case import RequestChannelTokenUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.errors import (
    ChannelAlreadyLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED

PROVIDER = "solapi"


class RequestChannelTokenInteractor(RequestChannelTokenUseCase):
    """관리자 카카오톡으로 6자리 토큰을 보내 달라고 업체에 요청하고 채널 줄을 token_requested 로 둔다(설계 6.2-1).

    업체 호출이 먼저, 저장이 뒤다 — 잠금을 쥔 채 업체를 부르지 않는다(N14). 검색 아이디·관리자 번호는 저장하지 않는다.
    """

    def __init__(self, channels: ChannelRepository, gateway: MessageGatewayPort, limiter: OnboardingLimiterPort) -> None:
        self._channels = channels
        self._gateway = gateway
        self._limiter = limiter

    async def request_channel_token(self, command: RequestChannelTokenCommand) -> None:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is not None and channel.is_linked:
            raise ChannelAlreadyLinkedError("이미 연동된 채널입니다. 다시 연동하려면 먼저 해제해 주세요.")
        if not await self._limiter.allow(ctx.shop_id, "token"):
            raise TooManyNotificationRequestsError("토큰 신청이 너무 잦습니다. 잠시 뒤 다시 시도해 주세요.")
        try:
            await self._gateway.request_channel_token(command.search_id, command.admin_phone, command.category_code)
        except GatewayError as exc:
            raise ProviderUnavailableError("발송 업체에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from exc
        if channel is None:
            channel = NotificationChannel(
                shop_id=ctx.shop_id, status=TOKEN_REQUESTED, provider=PROVIDER, provider_channel_id=None,
                linked_at=None, unlinked_at=None, sender_number=None, sender_number_verified_at=None,
                sms_fallback_enabled=False,
            )
        else:
            # 해제했던 매장을 되살린다 — 발신번호·인증 시각·문자 대체는 그대로 둔다.
            channel = replace(channel, status=TOKEN_REQUESTED, provider=PROVIDER, provider_channel_id=None,
                              linked_at=None)
        await self._channels.save(ctx, channel)
