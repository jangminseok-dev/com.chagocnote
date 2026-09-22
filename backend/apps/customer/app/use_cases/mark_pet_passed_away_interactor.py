from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand
from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class MarkPetPassedAwayInteractor(MarkPetPassedAwayUseCase):
    """무지개다리 — 기록은 남기고 목록 기본에서 숨긴다."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._today = today

    async def mark_pet_passed_away(self, command: MarkPetPassedAwayCommand) -> PetDetailView:
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.set_passed_away(command.ctx, command.pet_id, passed_away=True)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
