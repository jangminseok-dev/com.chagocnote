from __future__ import annotations

from datetime import datetime

from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.errors import PetNotFoundError, PetPassedAwayError
from hub.app.dtos.family_brief import FamilyBriefs
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
