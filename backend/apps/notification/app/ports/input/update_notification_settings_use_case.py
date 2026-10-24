from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.update_notification_settings_dto import UpdateNotificationSettingsCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView


class UpdateNotificationSettingsUseCase(ABC):
    @abstractmethod
    async def update_notification_settings(self, command: UpdateNotificationSettingsCommand) -> NotificationOverviewView: ...
