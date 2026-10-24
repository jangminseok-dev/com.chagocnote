from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.unlink_channel_dto import UnlinkChannelCommand


class UnlinkChannelUseCase(ABC):
    @abstractmethod
    async def unlink_channel(self, command: UnlinkChannelCommand) -> None: ...
