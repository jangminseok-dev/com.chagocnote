from __future__ import annotations

from core.database import DbSession
from notification.app.ports.input.get_notification_overview_use_case import GetNotificationOverviewUseCase
from notification.app.use_cases.get_notification_overview_interactor import GetNotificationOverviewInteractor
from notification.dependencies.notification_wiring import (
    build_channel_repository,
    build_settings_repository,
    build_template_repository,
)


def get_get_notification_overview_use_case(db: DbSession) -> GetNotificationOverviewUseCase:
    return GetNotificationOverviewInteractor(
        channels=build_channel_repository(db), settings=build_settings_repository(db),
        templates=build_template_repository(db),
    )
