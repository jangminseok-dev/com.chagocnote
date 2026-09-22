from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.get_pet_dto import GetPetQuery


class GetPetUseCase(ABC):
    @abstractmethod
    async def get_pet(self, query: GetPetQuery) -> PetDetailView: ...
