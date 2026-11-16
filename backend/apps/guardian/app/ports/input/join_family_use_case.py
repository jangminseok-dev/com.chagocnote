from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.family_dto import JoinFamilyCommand, JoinFamilyResult


class JoinFamilyUseCase(ABC):
    @abstractmethod
    async def join(self, command: JoinFamilyCommand) -> JoinFamilyResult: ...
