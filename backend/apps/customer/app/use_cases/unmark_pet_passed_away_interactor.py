from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.unmark_pet_passed_away_dto import UnmarkPetPassedAwayCommand
from customer.app.ports.input.unmark_pet_passed_away_use_case import UnmarkPetPassedAwayUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class UnmarkPetPassedAwayInteractor(UnmarkPetPassedAwayUseCase):
    """잘못 누른 무지개다리를 되돌린다."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._today = today

    async def unmark_pet_passed_away(self, command: UnmarkPetPassedAwayCommand) -> PetDetailView:
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.set_passed_away(command.ctx, command.pet_id, passed_away=False)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
