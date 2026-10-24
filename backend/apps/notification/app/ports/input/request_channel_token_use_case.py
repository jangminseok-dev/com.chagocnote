from __future__ import annotations

from abc import ABC, abstractmethod

from notification.app.dtos.request_channel_token_dto import RequestChannelTokenCommand


class RequestChannelTokenUseCase(ABC):
    @abstractmethod
    async def request_channel_token(self, command: RequestChannelTokenCommand) -> None: ...
