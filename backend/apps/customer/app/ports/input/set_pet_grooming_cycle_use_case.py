from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.set_pet_grooming_cycle_dto import SetPetGroomingCycleCommand


class SetPetGroomingCycleUseCase(ABC):
    @abstractmethod
    async def set_pet_grooming_cycle(self, command: SetPetGroomingCycleCommand) -> None: ...
