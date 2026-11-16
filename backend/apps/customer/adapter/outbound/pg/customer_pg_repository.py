from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.mappers.customer_mapper import to_customer
from customer.adapter.outbound.orm.customer_orm import CustomerOrm, PetConditionOrm, PetOrm
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.domain.entities.customer import Customer
from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenError
from customer.domain.value_objects.customer_profile import CustomerProfile
from hub.app.dtos.shop_context import ShopContext

_PHONE_UNIQUE = "uq_customers_shop_phone_active"


class CustomerPgRepository(CustomerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active(self, ctx: ShopContext):
        return select(CustomerOrm).where(
            CustomerOrm.shop_id == ctx.shop_id, CustomerOrm.deleted_at.is_(None)
        )

    async def find_active_by_phone(self, ctx: ShopContext, phone: str) -> Customer | None:
        row = (
            await self._session.execute(self._active(ctx).where(CustomerOrm.phone == phone))
        ).scalar_one_or_none()
        return to_customer(row) if row else None

    async def get_active(self, ctx: ShopContext, customer_id: int) -> Customer:
        return to_customer(await self._row(ctx, customer_id, lock=False))

    async def lock_active(self, ctx: ShopContext, customer_id: int) -> Customer:
        return to_customer(await self._row(ctx, customer_id, lock=True))

    async def list_active(self, ctx: ShopContext, customer_ids: list[int]) -> list[Customer]:
        rows = (
            await self._session.execute(self._active(ctx).where(CustomerOrm.id.in_(customer_ids)))
        ).scalars()
        return [to_customer(row) for row in rows]

    async def create(self, ctx: ShopContext, profile: CustomerProfile) -> Customer:
        row = CustomerOrm(
            shop_id=ctx.shop_id,
            name=profile.name,
            phone=profile.phone,
            phone_alt=profile.phone_alt,
            marketing_consent=profile.marketing_consent,
            marketing_consent_changed_at=func.now(),
            memo=profile.memo,
        )
        async with self._phone_guard():
            self._session.add(row)
            await self._session.flush()
        return to_customer(await self._row(ctx, row.id, lock=False))

    async def update(
        self, ctx: ShopContext, customer_id: int, profile: CustomerProfile, consent_changed: bool
    ) -> Customer:
        values = dict(
            name=profile.name,
            phone=profile.phone,
            phone_alt=profile.phone_alt,
            marketing_consent=profile.marketing_consent,
            memo=profile.memo,
            updated_at=func.now(),   # 값이 같아도 '수정'은 최근 활동이다(최근순 정렬)
        )
        if consent_changed:
            values["marketing_consent_changed_at"] = func.now()
        async with self._phone_guard():
            await self._session.execute(
                update(CustomerOrm)
                .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == ctx.shop_id,
                       CustomerOrm.deleted_at.is_(None))
                .values(**values)
            )
        return to_customer(await self._row(ctx, customer_id, lock=False))

    async def set_caution(
        self, ctx: ShopContext, customer_id: int, reason: str | None, until: date | None,
        member_id: int | None,
    ) -> Customer:
        # updated_at 은 건드리지 않는다 — 주의 표시는 고객 정보의 '수정'(최근순 정렬)이 아니다.
        await self._session.execute(
            update(CustomerOrm)
            .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == ctx.shop_id,
                   CustomerOrm.deleted_at.is_(None))
            .values(caution_reason=reason, caution_until=until,
                    caution_set_at=func.now() if reason is not None else None,
                    caution_set_by_member_id=member_id, updated_at=CustomerOrm.updated_at)
        )
        return to_customer(await self._row(ctx, customer_id, lock=False))

    async def anonymize(self, ctx: ShopContext, customer_id: int) -> None:
        await self._session.execute(
            update(CustomerOrm)
            .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == ctx.shop_id,
                   CustomerOrm.deleted_at.is_(None))
            .values(name=None, phone=None, phone_alt=None, memo=None, deleted_at=func.now(),
                    # 주의 사유는 사람에 대한 평가다 — 익명화와 함께 지운다(③-B C2).
                    caution_reason=None, caution_until=None, caution_set_at=None,
                    caution_set_by_member_id=None)
        )
        # 뒤따르는 두 문장도 ctx 소속으로 거른다 — customer_id 만으로 걸렀다가는 다른 매장 ctx 로
        # 불러도 그 customer_id 가 실존하는 다른 매장 소속이면 그 반려동물·질병까지 지워 버린다.
        owned_customer = select(CustomerOrm.id).where(
            CustomerOrm.id == customer_id, CustomerOrm.shop_id == ctx.shop_id
        )
        await self._session.execute(
            delete(PetConditionOrm).where(
                PetConditionOrm.pet_id.in_(
                    select(PetOrm.id).where(PetOrm.customer_id.in_(owned_customer))
                )
            )
        )
        await self._session.execute(
            update(PetOrm)
            .where(PetOrm.customer_id.in_(owned_customer))
            .values(name=None, memo=None, grooming_consent_on=None, grooming_consent_by_member_id=None,
                    grooming_consent_signature_id=None, grooming_cycle_weeks=None, revisit_nudged_on=None)
        )

    async def _row(self, ctx: ShopContext, customer_id: int, lock: bool) -> CustomerOrm:
        # 잠근 뒤 다시 읽을 때 세션에 남은 옛 값을 보지 않는다.
        stmt = self._active(ctx).where(CustomerOrm.id == customer_id).execution_options(
            populate_existing=True
        )
        if lock:
            stmt = stmt.with_for_update()
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise CustomerNotFoundError("고객을 찾을 수 없습니다.")
        return row

    @asynccontextmanager
    async def _phone_guard(self):
        """번호 유일 색인 위반을 CUSTOMER_PHONE_TAKEN 으로 바꾼다. 세이브포인트라 트랜잭션은 계속 쓸 수 있다.

        같은 번호를 동시에 넣는 두 요청 중 늦은 쪽은 앞선 쪽이 커밋할 때까지 색인에서 기다렸다가 여기서 걸린다.
        """
        try:
            async with self._session.begin_nested():
                yield
        except IntegrityError as exc:
            self._raise_if_phone_taken(exc)
            raise

    @staticmethod
    def _raise_if_phone_taken(exc: IntegrityError) -> None:
        if getattr(exc.orig.__cause__, "constraint_name", None) == _PHONE_UNIQUE:
            raise CustomerPhoneTakenError("이미 등록된 전화번호입니다.") from exc
