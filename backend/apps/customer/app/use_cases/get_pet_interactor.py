from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.get_pet_dto import GetPetQuery
from customer.app.ports.input.get_pet_use_case import GetPetUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class GetPetInteractor(GetPetUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._today = today

    async def get_pet(self, query: GetPetQuery) -> PetDetailView:
        return await read_pet_detail(query.ctx, query.pet_id, self._customers, self._pets, self._today())
