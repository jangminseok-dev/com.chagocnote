from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand
from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.consent_forms import drop_pets
from customer.app.services.detail_reader import read_pet_detail
from customer.domain.errors import PetHasUpcomingVisitsError
from hub.app.ports.visit_ledger_port import VisitLedgerPort


class MarkPetPassedAwayInteractor(MarkPetPassedAwayUseCase):
    """무지개다리 — 기록은 남기고 목록 기본에서 숨긴다."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        ledger: VisitLedgerPort, today: Callable[[], date], forms: ConsentFormRepository,
        now: Callable[[], datetime],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._ledger = ledger
        self._today = today
        self._forms = forms
        self._now = now

    async def mark_pet_passed_away(self, command: MarkPetPassedAwayCommand) -> PetDetailView:
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        if await self._ledger.pet_has_upcoming(command.ctx, command.pet_id):
            raise PetHasUpcomingVisitsError("앞으로의 예약이 남아 있습니다. 예약을 먼저 취소해 주세요.")
        await self._pets.set_passed_away(command.ctx, command.pet_id, passed_away=True)
        # 살아 있는 동의서 링크에서 덜어 낸다(⑪). 서명 기록은 남는다.
        await drop_pets(command.ctx, customer_id, [command.pet_id], self._now(), self._forms)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
