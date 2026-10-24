from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from notification.app.ports.input.update_notification_settings_use_case import UpdateNotificationSettingsUseCase
from notification.app.ports.output.message_gateway_port import MessageGatewayPort
from notification.app.use_cases.update_notification_settings_interactor import (
    UpdateNotificationSettingsInteractor,
)
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_message_repository,
    build_settings_repository,
    build_template_repository,
    get_message_gateway,
)
from notification.domain.services.clock import utc_now


def get_update_notification_settings_use_case(
    db: DbSession, gateway: MessageGatewayPort = Depends(get_message_gateway),
) -> UpdateNotificationSettingsUseCase:
    return UpdateNotificationSettingsInteractor(
        channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db), messages=build_message_repository(db), gateway=gateway, now=utc_now,
    )
