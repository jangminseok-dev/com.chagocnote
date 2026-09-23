from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.customer_orm import CustomerOrm, PetOrm
from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
from customer.domain.services.phone_number import mask_phone
from hub.app.dtos.family_brief import CustomerBrief, PetBrief
from hub.app.dtos.shop_context import ShopContext


class FamilyBriefPgRepository(FamilyBriefRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_customer_briefs(self, ctx: ShopContext, customer_ids: list[int]) -> list[CustomerBrief]:
        rows = (
            await self._session.execute(
                select(CustomerOrm.id, CustomerOrm.name, CustomerOrm.phone).where(
                    CustomerOrm.id.in_(customer_ids), CustomerOrm.shop_id == ctx.shop_id
                )
            )
        ).all()
        return [
            CustomerBrief(customer_id=id_, name=name, phone_masked=mask_phone(phone) if phone else None)
            for id_, name, phone in rows
        ]

    async def list_pet_briefs(self, ctx: ShopContext, pet_ids: list[int]) -> list[PetBrief]:
        rows = (
            await self._session.execute(
                select(PetOrm)
                .join(CustomerOrm, CustomerOrm.id == PetOrm.customer_id)
                .where(PetOrm.id.in_(pet_ids), CustomerOrm.shop_id == ctx.shop_id)
            )
        ).scalars()
        return [
            PetBrief(pet_id=p.id, customer_id=p.customer_id, name=p.name, species=p.species,
                     breed=p.breed, weight_kg=p.weight_kg, passed_away=p.passed_away_at is not None)
            for p in rows
        ]
