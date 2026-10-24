from __future__ import annotations

from notification.app.dtos.request_sender_verification_dto import RequestSenderVerificationCommand
from notification.app.ports.input.request_sender_verification_use_case import RequestSenderVerificationUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import GatewayError, MessageGatewayPort
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.domain.errors import (
    ChannelNotLinkedError,
    ProviderUnavailableError,
    TooManyNotificationRequestsError,
)


class RequestSenderVerificationInteractor(RequestSenderVerificationUseCase):
    """문자 대체용 발신번호의 본인인증을 시작한다(설계 6.2-4). 아무것도 저장하지 않는다."""

    def __init__(self, channels: ChannelRepository, gateway: MessageGatewayPort, limiter: OnboardingLimiterPort) -> None:
        self._channels = channels
        self._gateway = gateway
        self._limiter = limiter

    async def request_sender_verification(self, command: RequestSenderVerificationCommand) -> None:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("먼저 카카오톡 채널을 연동해 주세요.")
        if not await self._limiter.allow(ctx.shop_id, "sender_verification"):
            raise TooManyNotificationRequestsError("인증 요청이 너무 잦습니다. 잠시 뒤 다시 시도해 주세요.")
        try:
            await self._gateway.request_sender_verification(command.phone)
        except GatewayError as exc:
            raise ProviderUnavailableError("발송 업체에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from exc
