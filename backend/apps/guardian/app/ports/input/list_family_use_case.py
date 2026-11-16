from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.family_dto import FamilyMemberView, ListFamilyQuery


class ListFamilyUseCase(ABC):
    @abstractmethod
    async def list_family(self, command: ListFamilyQuery) -> list[FamilyMemberView]: ...
