from __future__ import annotations

from notification.adapter.outbound.log_notification_myself_record_adapter import (
    LogNotificationMyselfRecordAdapter,
)
from notification.app.ports.input.notification_myself_use_case import NotificationMyselfUseCase
from notification.app.use_cases.notification_myself_interactor import NotificationMyselfInteractor


def get_notification_myself_use_case() -> NotificationMyselfUseCase:
    return NotificationMyselfInteractor(record=LogNotificationMyselfRecordAdapter())
