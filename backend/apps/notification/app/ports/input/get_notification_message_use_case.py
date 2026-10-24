from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.get_notification_message_dto import GetNotificationMessageQuery
from notification.app.dtos.notification_message_dto import NotificationMessageView


class GetNotificationMessageUseCase(ABC):
    @abstractmethod
    async def get_notification_message(self, query: GetNotificationMessageQuery) -> NotificationMessageView: ...
