from __future__ import annotations

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.mappers.customer_mapper import to_pet
from customer.adapter.outbound.orm.customer_orm import (
    CustomerOrm,
    PetConditionOrm,
    PetConditionTypeOrm,
    PetOrm,
)
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.entities.pet import Pet, PetCondition
from customer.domain.errors import PetNotFoundError
from customer.domain.value_objects.pet_profile import PetProfile
from hub.app.dtos.shop_context import ShopContext


def _owner_ids(ctx: ShopContext):
    """이 매장의 살아 있는 고객 ID. 반려동물의 소속은 언제나 이것으로 거른다."""
    return select(CustomerOrm.id).where(
        CustomerOrm.shop_id == ctx.shop_id, CustomerOrm.deleted_at.is_(None)
    )


def _profile_values(profile: PetProfile) -> dict:
    return dict(
        name=profile.name, species=profile.species, breed=profile.breed, sex=profile.sex,
        neutered=profile.neutered, birth_date=profile.birth_date, birth_year=profile.birth_year,
        weight_kg=profile.weight_kg, no_known_conditions=profile.no_known_conditions,
        memo=profile.memo,
    )


class PetPgRepository(PetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _owned(self, ctx: ShopContext):
        return select(PetOrm).where(PetOrm.customer_id.in_(_owner_ids(ctx)))

    async def get(self, ctx: ShopContext, pet_id: int) -> Pet:
        row = (
            await self._session.execute(
                self._owned(ctx).where(PetOrm.id == pet_id).execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
        conditions = await self._conditions([row.id])
        return to_pet(row, conditions.get(row.id, []))

    async def lock_owner(self, ctx: ShopContext, pet_id: int) -> int:
        # 잠금을 기다리는 사이 고객이 익명화되면, 풀려난 뒤 WHERE 를 다시 평가해 행이 빠진다 → 404.
        customer_id = (
            await self._session.execute(
                select(CustomerOrm.id)
                .join(PetOrm, PetOrm.customer_id == CustomerOrm.id)
                .where(PetOrm.id == pet_id, CustomerOrm.shop_id == ctx.shop_id,
                       CustomerOrm.deleted_at.is_(None))
                .with_for_update(of=CustomerOrm)
            )
        ).scalar_one_or_none()
        if customer_id is None:
            raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
        return customer_id

    async def list_for_customers(self, ctx: ShopContext, customer_ids: list[int]) -> list[Pet]:
        rows = (
            await self._session.execute(
                self._owned(ctx)
                .where(PetOrm.customer_id.in_(customer_ids))
                .order_by(PetOrm.customer_id, PetOrm.id)
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        conditions = await self._conditions([row.id for row in rows])
        return [to_pet(row, conditions.get(row.id, [])) for row in rows]

    async def add(self, ctx: ShopContext, customer_id: int, profile: PetProfile) -> Pet:
        pet_id = (
            await self._session.execute(
                insert(PetOrm)
                .values(customer_id=customer_id, **_profile_values(profile))
                .returning(PetOrm.id)
            )
        ).scalar_one()
        await self._insert_conditions(pet_id, profile)
        return await self.get(ctx, pet_id)   # 다른 매장의 고객이면 여기서 404 가 되고 요청째 되돌린다

    async def update(self, ctx: ShopContext, pet_id: int, profile: PetProfile) -> Pet:
        # 질병 행을 지우기 전에 소속부터 확인한다(반려동물 → 고객 → shop_id). 소속 확인 전에
        # 지웠다가 되돌리는 방식은 커밋 여부에 상관없이 다른 세션이 그 사이 빈 상태를 볼 수 있다.
        owned = (
            await self._session.execute(
                select(PetOrm.id).where(PetOrm.id == pet_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
            )
        ).scalar_one_or_none()
        if owned is None:
            raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
        await self._session.execute(
            update(PetOrm)
            .where(PetOrm.id == pet_id)
            .values(**_profile_values(profile), updated_at=func.now())
        )
        await self._session.execute(delete(PetConditionOrm).where(PetConditionOrm.pet_id == pet_id))
        await self._insert_conditions(pet_id, profile)
        return await self.get(ctx, pet_id)

    async def set_passed_away(self, ctx: ShopContext, pet_id: int, passed_away: bool) -> Pet:
        # 이미 무지개다리면 처음 시각을 지킨다.
        stamp = func.coalesce(PetOrm.passed_away_at, func.now()) if passed_away else None
        await self._session.execute(
            update(PetOrm)
            .where(PetOrm.id == pet_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
            .values(passed_away_at=stamp, updated_at=func.now())
        )
        return await self.get(ctx, pet_id)

    async def count_for_customer(self, ctx: ShopContext, customer_id: int) -> int:
        return (
            await self._session.execute(
                select(func.count())
                .select_from(PetOrm)
                .where(PetOrm.customer_id == customer_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
            )
        ).scalar_one()

    async def delete(self, ctx: ShopContext, pet_id: int) -> None:
        await self._session.execute(
            delete(PetOrm).where(PetOrm.id == pet_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
        )

    async def _insert_conditions(self, pet_id: int, profile: PetProfile) -> None:
        if profile.conditions:
            await self._session.execute(
                insert(PetConditionOrm),
                [
                    dict(pet_id=pet_id, type_code=c.type_code, custom_label=c.custom_label, note=c.note)
                    for c in profile.conditions
                ],
            )

    async def _conditions(self, pet_ids: list[int]) -> dict[int, list[PetCondition]]:
        rows = (
            await self._session.execute(
                select(PetConditionOrm, PetConditionTypeOrm.label)
                .join(PetConditionTypeOrm, PetConditionTypeOrm.code == PetConditionOrm.type_code)
                .where(PetConditionOrm.pet_id.in_(pet_ids))
                .order_by(PetConditionTypeOrm.sort_order, PetConditionOrm.id)
            )
        ).all()
        found: dict[int, list[PetCondition]] = {}
        for row, label in rows:
            found.setdefault(row.pet_id, []).append(
                PetCondition(type_code=row.type_code, label=label,
                             custom_label=row.custom_label, note=row.note)
            )
        return found
