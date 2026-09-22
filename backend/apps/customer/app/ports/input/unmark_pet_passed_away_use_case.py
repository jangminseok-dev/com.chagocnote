from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.unmark_pet_passed_away_dto import UnmarkPetPassedAwayCommand


class UnmarkPetPassedAwayUseCase(ABC):
    @abstractmethod
    async def unmark_pet_passed_away(self, command: UnmarkPetPassedAwayCommand) -> PetDetailView: ...
