from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.guardian_report_dto import GuardianPetView, ListGuardianPetsQuery


class ListGuardianPetsUseCase(ABC):
    @abstractmethod
    async def list_pets(self, query: ListGuardianPetsQuery) -> list[GuardianPetView]: ...
