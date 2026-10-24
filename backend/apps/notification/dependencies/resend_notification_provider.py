from __future__ import annotations

from core.database import DbSession
from notification.app.ports.input.resend_notification_use_case import ResendNotificationUseCase
from notification.app.services.dispatcher_wakeup import wake
from notification.app.use_cases.resend_notification_interactor import ResendNotificationInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_message_repository,
    build_template_repository,
)
from notification.domain.services.clock import utc_now


def get_resend_notification_use_case(db: DbSession) -> ResendNotificationUseCase:
    return ResendNotificationInteractor(
        channels=build_channel_repository(db), templates=build_template_repository(db),
        messages=build_message_repository(db), now=utc_now, wake=wake,
    )
