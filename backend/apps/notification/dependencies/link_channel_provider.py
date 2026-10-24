from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from notification.app.ports.input.link_channel_use_case import LinkChannelUseCase
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.use_cases.link_channel_interactor import LinkChannelInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_onboarding_limiter,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.clock import utc_now


def get_link_channel_use_case(
    db: DbSession, gateway: MessageGatewayPort = Depends(get_message_gateway),
) -> LinkChannelUseCase:
    return LinkChannelInteractor(
        channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db), gateway=gateway, limiter=build_onboarding_limiter(), now=utc_now,
    )
