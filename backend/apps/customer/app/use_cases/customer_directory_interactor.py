from __future__ import annotations

from datetime import datetime

DRAFT_CANDIDATE_LIMIT = 5
_MATCH_LIMIT = 20   # 순위를 매기기 전에 읽는 가족 수 — 낱말 하나에 수십 가족이 걸려도 여기서 자른다

from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.errors import PetNotFoundError, PetPassedAwayError
from customer.domain.services.phone_number import mask_phone
from customer.domain.services.search_terms import parse_query
from hub.app.dtos.draft_candidate import DraftCandidate
from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort


class CustomerDirectoryInteractor(CustomerDirectoryPort):
    """허브의 CustomerDirectoryPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, briefs: FamilyBriefRepository,
        search: CustomerSearchPort,
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._briefs = briefs
        self._search = search

    async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
        # 가족을 바꾸는 customer 유스케이스와 같은 잠금이다 — 익명화와 예약 생성이 서로를 기다린다.
        await self._customers.lock_active(ctx, customer_id)
        if not pet_ids:
            return
        family = {pet.id: pet for pet in await self._pets.list_for_customers(ctx, [customer_id])}
        for pet_id in pet_ids:
            if pet_id not in family:
                raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
            if family[pet_id].passed_away:
                raise PetPassedAwayError("무지개다리를 건넌 아이에게는 예약을 잡을 수 없습니다.")

    async def briefs(self, ctx: ShopContext, customer_ids: list[int], pet_ids: list[int]) -> FamilyBriefs:
        customers = await self._briefs.list_customer_briefs(ctx, customer_ids) if customer_ids else []
        pets = await self._briefs.list_pet_briefs(ctx, pet_ids) if pet_ids else []
        return FamilyBriefs(
            customers={c.customer_id: c for c in customers}, pets={p.pet_id: p for p in pets}
        )

    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
        await self._search.set_last_visit(ctx, customer_id, at)

    async def find_draft_candidates(self, ctx: ShopContext, words: tuple[str, ...]) -> list[DraftCandidate]:
        if not words:
            return []
        customer_ids = await self._search.match_any(ctx, parse_query(" ".join(words)), limit=_MATCH_LIMIT)
        if not customer_ids:
            return []
        customers = await self._customers.list_active(ctx, customer_ids)   # 익명화한 고객은 여기서 빠진다
        pets_of = {c.id: [] for c in customers}
        for pet in await self._pets.list_for_customers(ctx, [c.id for c in customers]):
            if not pet.passed_away:
                pets_of[pet.customer_id].append(pet)
        digits = [w for w in words if w.isdigit()]
        ranked = []
        for customer in customers:
            matched = tuple(p.id for p in pets_of[customer.id] if p.name in words)
            if matched:
                rank = 0
            elif customer.name in words:
                rank = 1
            elif any((len(d) >= 8 and d in customer.phone) or (len(d) == 4 and customer.phone.endswith(d))
                     for d in digits):
                rank = 2
            else:
                rank = 3
            ranked.append((rank, customer.id, customer, matched))
        ranked.sort(key=lambda r: (r[0], r[1]))
        return [
            DraftCandidate(
                customer=CustomerBrief(customer_id=c.id, name=c.name, phone_masked=mask_phone(c.phone)),
                pets=tuple(
                    PetBrief(pet_id=p.id, customer_id=c.id, name=p.name, species=p.species, breed=p.breed,
                             weight_kg=p.weight_kg, passed_away=False)
                    for p in pets_of[c.id]
                ),
                matched_pet_ids=matched,
                exact=rank <= 1,
            )
            for rank, _, c, matched in ranked[:DRAFT_CANDIDATE_LIMIT]
        ]
