from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand, UnlinkIdentityResult


class UnlinkIdentityUseCase(ABC):
    @abstractmethod
    async def unlink(self, command: UnlinkIdentityCommand) -> UnlinkIdentityResult: ...
