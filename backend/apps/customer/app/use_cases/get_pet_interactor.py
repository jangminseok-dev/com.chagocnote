from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetOverviewView
from customer.app.dtos.get_pet_dto import GetPetQuery
from customer.app.ports.input.get_pet_use_case import GetPetUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail
from customer.app.services.pet_photos import pet_photos
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


class GetPetInteractor(GetPetUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, ledger: VisitLedgerPort,
        library: MediaLibraryPort, today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._ledger = ledger
        self._library = library
        self._today = today

    async def get_pet(self, query: GetPetQuery) -> PetOverviewView:
        detail = await read_pet_detail(query.ctx, query.pet_id, self._customers, self._pets, self._today())
        photos = await pet_photos(query.ctx, [query.pet_id], self._ledger, self._library)
        # 주기는 visit 이 계산한다(⑬) — 직접 정한 값만 넘긴다. customer 는 계산 규칙을 모른다.
        revisit = await self._ledger.pet_revisit(query.ctx, query.pet_id, detail.pet.grooming_cycle_weeks)
        return PetOverviewView(detail=detail, photo=photos.get(query.pet_id), revisit=revisit)
