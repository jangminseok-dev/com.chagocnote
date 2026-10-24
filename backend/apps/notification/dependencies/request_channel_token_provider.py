from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from notification.app.ports.input.request_channel_token_use_case import RequestChannelTokenUseCase
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.use_cases.request_channel_token_interactor import RequestChannelTokenInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_onboarding_limiter,
    get_message_gateway,
)


def get_request_channel_token_use_case(
    db: DbSession, gateway: MessageGatewayPort = Depends(get_message_gateway),
) -> RequestChannelTokenUseCase:
    return RequestChannelTokenInteractor(
        channels=build_channel_repository(db), gateway=gateway, limiter=build_onboarding_limiter())
