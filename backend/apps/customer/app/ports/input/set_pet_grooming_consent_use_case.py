from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.set_pet_grooming_consent_dto import SetPetGroomingConsentCommand


class SetPetGroomingConsentUseCase(ABC):
    @abstractmethod
    async def set_pet_grooming_consent(self, command: SetPetGroomingConsentCommand) -> PetDetailView: ...
