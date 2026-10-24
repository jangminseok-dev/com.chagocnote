from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.link_channel_dto import LinkChannelCommand
from notification.app.dtos.notification_overview_dto import NotificationOverviewView


class LinkChannelUseCase(ABC):
    @abstractmethod
    async def link_channel(self, command: LinkChannelCommand) -> NotificationOverviewView: ...
