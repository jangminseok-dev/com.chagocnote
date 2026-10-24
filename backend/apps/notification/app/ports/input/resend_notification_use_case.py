from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.resend_notification_dto import ResendNotificationCommand


class ResendNotificationUseCase(ABC):
    @abstractmethod
    async def resend_notification(self, command: ResendNotificationCommand) -> int:
        """새 줄의 message_id."""
