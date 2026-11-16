from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.family_dto import EndAllFamilyCommand


class EndAllFamilyUseCase(ABC):
    @abstractmethod
    async def end_all(self, command: EndAllFamilyCommand) -> None: ...
