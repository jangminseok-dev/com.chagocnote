from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.set_pet_grooming_consent_dto import SetPetGroomingConsentCommand
from customer.app.ports.input.set_pet_grooming_consent_use_case import SetPetGroomingConsentUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail
from customer.domain.services.care_marks import check_consent_day


class SetPetGroomingConsentInteractor(SetPetGroomingConsentUseCase):
    """미용 동의를 받았다고 적는다(③-B 3.2) — 가장 최근에 받은 날 하나와 적은 멤버. 노령·지병이 아닌 아이에게도 적을 수 있다."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._today = today

    async def set_pet_grooming_consent(self, command: SetPetGroomingConsentCommand) -> PetDetailView:
        today = self._today()
        received_on = command.received_on or today
        check_consent_day(received_on, today)
        await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.set_grooming_consent(
            command.ctx, command.pet_id, received_on, command.ctx.member_id
        )
        return await read_pet_detail(command.ctx, command.pet_id, self._customers, self._pets, today)
