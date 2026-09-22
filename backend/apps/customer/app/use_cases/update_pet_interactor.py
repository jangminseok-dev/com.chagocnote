from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.ports.input.update_pet_use_case import UpdatePetUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class UpdatePetInteractor(UpdatePetUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository,
        condition_types: ConditionTypeRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._search = search
        self._today = today

    async def update_pet(self, command: UpdatePetCommand) -> PetDetailView:
        codes = frozenset(t.code for t in await self._condition_types.list_all())
        profile = command.pet.to_profile(codes, self._today())
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.update(command.ctx, command.pet_id, profile)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
