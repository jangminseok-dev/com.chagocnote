from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.grant_operator_dto import GrantOperatorCommand


class GrantOperatorUseCase(ABC):
    @abstractmethod
    async def grant(self, command: GrantOperatorCommand) -> None: ...
