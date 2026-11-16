from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.consent_orm import CustomerFormOrm
from customer.app.ports.output.intake_form_repository import IntakeFormRepository
from customer.domain.entities.intake import IntakeForm
from hub.app.dtos.shop_context import ShopContext

_KIND = "intake"


def _form(row: CustomerFormOrm) -> IntakeForm:
    return IntakeForm(
        id=row.id, shop_id=row.shop_id, public_id=bytes(row.public_id), customer_id=row.customer_id,
        pet_id=row.intake_pet_id, expires_at=row.expires_at, revoked_at=row.revoked_at,
        submitted_at=row.submitted_at, created_by_member_id=row.created_by_member_id, created_at=row.created_at,
        answered=row.intake_answered,
    )


class IntakeFormPgRepository(IntakeFormRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _one(self, statement) -> IntakeForm | None:
        row = (await self._session.execute(statement.execution_options(populate_existing=True))).scalars().first()
        return None if row is None else _form(row)

    @staticmethod
    def _live(ctx: ShopContext, now: datetime):
        return select(CustomerFormOrm).where(
            CustomerFormOrm.shop_id == ctx.shop_id, CustomerFormOrm.kind == _KIND,
            CustomerFormOrm.revoked_at.is_(None), CustomerFormOrm.submitted_at.is_(None),
            CustomerFormOrm.expires_at > now,
        )

    async def create(
        self, ctx: ShopContext, customer_id: int | None, pet_id: int | None, public_id: bytes, expires_at: datetime,
    ) -> IntakeForm:
        form_id = (
            await self._session.execute(
                insert(CustomerFormOrm).values(
                    shop_id=ctx.shop_id, kind=_KIND, public_id=public_id, customer_id=customer_id,
                    intake_pet_id=pet_id, expires_at=expires_at, created_by_member_id=ctx.member_id,
                ).returning(CustomerFormOrm.id)
            )
        ).scalar_one()
        return await self._one(select(CustomerFormOrm).where(CustomerFormOrm.id == form_id))

    async def live_for(self, ctx: ShopContext, customer_id: int, pet_id: int | None, now: datetime) -> IntakeForm | None:
        target = CustomerFormOrm.intake_pet_id.is_(None) if pet_id is None else CustomerFormOrm.intake_pet_id == pet_id
        return await self._one(
            self._live(ctx, now).where(CustomerFormOrm.customer_id == customer_id, target)
            .order_by(CustomerFormOrm.id).with_for_update())

    async def close_expired(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        await self._session.execute(
            update(CustomerFormOrm)
            .where(CustomerFormOrm.shop_id == ctx.shop_id, CustomerFormOrm.customer_id == customer_id,
                   CustomerFormOrm.kind == _KIND, CustomerFormOrm.revoked_at.is_(None),
                   CustomerFormOrm.submitted_at.is_(None), CustomerFormOrm.expires_at <= now)
            .values(revoked_at=now)
        )

    async def list_live(self, ctx: ShopContext, now: datetime) -> list[IntakeForm]:
        rows = (
            await self._session.execute(
                self._live(ctx, now).order_by(CustomerFormOrm.created_at.desc(), CustomerFormOrm.id.desc())
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        return [_form(row) for row in rows]

    async def get(self, ctx: ShopContext, form_id: int) -> IntakeForm | None:
        return await self._one(select(CustomerFormOrm).where(
            CustomerFormOrm.id == form_id, CustomerFormOrm.shop_id == ctx.shop_id, CustomerFormOrm.kind == _KIND))

    async def revoke(self, ctx: ShopContext, form_id: int, now: datetime) -> None:
        await self._session.execute(
            update(CustomerFormOrm)
            .where(CustomerFormOrm.id == form_id, CustomerFormOrm.shop_id == ctx.shop_id,
                   CustomerFormOrm.kind == _KIND, CustomerFormOrm.revoked_at.is_(None),
                   CustomerFormOrm.submitted_at.is_(None))
            .values(revoked_at=now)
        )

    async def close_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        await self._session.execute(
            update(CustomerFormOrm)
            .where(CustomerFormOrm.shop_id == ctx.shop_id, CustomerFormOrm.customer_id == customer_id,
                   CustomerFormOrm.kind == _KIND, CustomerFormOrm.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def close_for_pet(self, ctx: ShopContext, pet_id: int, now: datetime, *, detach: bool) -> None:
        mine = (CustomerFormOrm.shop_id == ctx.shop_id, CustomerFormOrm.kind == _KIND,
                CustomerFormOrm.intake_pet_id == pet_id)
        await self._session.execute(
            update(CustomerFormOrm).where(*mine, CustomerFormOrm.revoked_at.is_(None)).values(revoked_at=now))
        if detach:
            await self._session.execute(update(CustomerFormOrm).where(*mine).values(intake_pet_id=None))

    async def find_public(self, public_id: bytes) -> IntakeForm | None:
        return await self._one(select(CustomerFormOrm).where(
            CustomerFormOrm.public_id == public_id, CustomerFormOrm.kind == _KIND))

    async def lock(self, form_id: int) -> IntakeForm | None:
        return await self._one(
            select(CustomerFormOrm).where(CustomerFormOrm.id == form_id, CustomerFormOrm.kind == _KIND)
            .with_for_update())

    async def mark_submitted(self, form_id: int, now: datetime) -> None:
        await self._session.execute(
            update(CustomerFormOrm)
            .where(CustomerFormOrm.id == form_id, CustomerFormOrm.submitted_at.is_(None))
            .values(submitted_at=now)
        )
