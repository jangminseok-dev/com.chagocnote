from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.logout_dto import LogoutCommand


class LogoutUseCase(ABC):
    @abstractmethod
    async def logout(self, command: LogoutCommand) -> None: ...
