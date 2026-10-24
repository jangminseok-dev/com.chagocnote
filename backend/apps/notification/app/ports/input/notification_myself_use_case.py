from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.notification_myself_dto import NotificationMyselfQuery, NotificationMyselfResponse


class NotificationMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: NotificationMyselfQuery) -> NotificationMyselfResponse: ...
