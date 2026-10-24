from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.confirm_sender_dto import ConfirmSenderCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView


class ConfirmSenderUseCase(ABC):
    @abstractmethod
    async def confirm_sender(self, command: ConfirmSenderCommand) -> NotificationOverviewView: ...
