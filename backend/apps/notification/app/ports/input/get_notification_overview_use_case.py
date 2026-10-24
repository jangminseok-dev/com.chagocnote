from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.get_notification_overview_dto import GetNotificationOverviewQuery
from notification.app.dtos.notification_overview_dto import NotificationOverviewView


class GetNotificationOverviewUseCase(ABC):
    @abstractmethod
    async def get_notification_overview(self, query: GetNotificationOverviewQuery) -> NotificationOverviewView: ...
