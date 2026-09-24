from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_search_dto import SearchRequest
from customer.app.dtos.list_customers_dto import (
    CustomerListView,
    FamilyCardView,
    ListCustomersQuery,
    PetSummaryView,
)
from customer.app.ports.input.list_customers_use_case import ListCustomersUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.services.pet_age import age_label
from customer.domain.services.phone_number import mask_phone
from customer.app.services.pet_photos import pet_photos
from customer.domain.services.search_terms import parse_query
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


class ListCustomersInteractor(ListCustomersUseCase):
    """검색 포트로 가족 ID 를 찾고, 보여 줄 정보는 원본 표에서 읽는다(검색 줄은 찾기와 정렬에만 쓴다)."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        ledger: VisitLedgerPort, library: MediaLibraryPort, today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._ledger = ledger
        self._library = library
        self._today = today

    async def list_customers(self, query: ListCustomersQuery) -> CustomerListView:
        words = parse_query(query.q)
        page = await self._search.search(
            query.ctx,
            SearchRequest(words=words, sort=query.sort, include_passed=query.include_passed,
                          cursor=query.cursor),
        )
        customers = {c.id: c for c in await self._customers.list_active(query.ctx, page.customer_ids)}
        pets_by_customer: dict[int, list] = {}
        for pet in await self._pets.list_for_customers(query.ctx, page.customer_ids):
            if query.include_passed or not pet.passed_away:
                pets_by_customer.setdefault(pet.customer_id, []).append(pet)

        today = self._today()
        photos = await pet_photos(
            query.ctx, [p.id for family in pets_by_customer.values() for p in family], self._ledger, self._library
        )
        items = [
            FamilyCardView(
                customer_id=customer_id,
                name=customers[customer_id].name,
                phone_masked=mask_phone(customers[customer_id].phone),
                pets=[
                    PetSummaryView(
                        pet_id=p.id, name=p.name, species=p.species, breed=p.breed,
                        age_label=age_label(p.birth_date, p.birth_year, today),
                        has_conditions=p.has_conditions, passed_away=p.passed_away, photo=photos.get(p.id),
                    )
                    for p in pets_by_customer.get(customer_id, [])
                ],
            )
            for customer_id in page.customer_ids
            if customer_id in customers   # 검색 줄과 원본이 어긋났으면(익명화 직후 등) 원본을 따른다
        ]
        pet_count = await self._search.count_pets(query.ctx, words, query.include_passed)
        return CustomerListView(items=items, next_cursor=page.next_cursor, pet_count=pet_count)
