from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.clear_pet_grooming_consent_dto import ClearPetGroomingConsentCommand
from customer.app.ports.input.clear_pet_grooming_consent_use_case import ClearPetGroomingConsentUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class ClearPetGroomingConsentInteractor(ClearPetGroomingConsentUseCase):
    """미용 동의 표시를 지운다. 없던 것을 지워도 된다(멱등)."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._today = today

    async def clear_pet_grooming_consent(self, command: ClearPetGroomingConsentCommand) -> PetDetailView:
        await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.set_grooming_consent(command.ctx, command.pet_id, None, None)
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
