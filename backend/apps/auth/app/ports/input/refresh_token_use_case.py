from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.dtos.token_dto import TokenPair


class RefreshTokenUseCase(ABC):
    @abstractmethod
    async def refresh(self, command: RefreshTokenCommand) -> TokenPair: ...
