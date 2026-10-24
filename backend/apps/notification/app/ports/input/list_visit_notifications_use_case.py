from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.list_visit_notifications_dto import ListVisitNotificationsQuery
from notification.app.dtos.notification_message_dto import NotificationMessageView


class ListVisitNotificationsUseCase(ABC):
    @abstractmethod
    async def list_visit_notifications(self, query: ListVisitNotificationsQuery) -> list[NotificationMessageView]: ...
