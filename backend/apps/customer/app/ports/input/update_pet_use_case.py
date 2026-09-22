from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.update_pet_dto import UpdatePetCommand


class UpdatePetUseCase(ABC):
    @abstractmethod
    async def update_pet(self, command: UpdatePetCommand) -> PetDetailView: ...
