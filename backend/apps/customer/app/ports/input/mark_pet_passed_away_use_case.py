from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand


class MarkPetPassedAwayUseCase(ABC):
    @abstractmethod
    async def mark_pet_passed_away(self, command: MarkPetPassedAwayCommand) -> PetDetailView: ...
