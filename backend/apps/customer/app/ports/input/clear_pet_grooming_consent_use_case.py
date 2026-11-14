from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.clear_pet_grooming_consent_dto import ClearPetGroomingConsentCommand


class ClearPetGroomingConsentUseCase(ABC):
    @abstractmethod
    async def clear_pet_grooming_consent(self, command: ClearPetGroomingConsentCommand) -> PetDetailView: ...
