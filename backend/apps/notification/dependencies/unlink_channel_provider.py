from __future__ import annotations

from core.database import DbSession
from notification.app.ports.input.unlink_channel_use_case import UnlinkChannelUseCase
from notification.app.use_cases.unlink_channel_interactor import UnlinkChannelInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_message_repository,
    build_template_repository,
)
from notification.domain.services.clock import utc_now


def get_unlink_channel_use_case(db: DbSession) -> UnlinkChannelUseCase:
    return UnlinkChannelInteractor(
        channels=build_channel_repository(db), templates=build_template_repository(db),
        messages=build_message_repository(db), now=utc_now,
    )
