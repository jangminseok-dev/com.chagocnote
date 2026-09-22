from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.dtos.customer_view_dto import PetDetailView


class AddPetUseCase(ABC):
    @abstractmethod
    async def add_pet(self, command: AddPetCommand) -> PetDetailView: ...
