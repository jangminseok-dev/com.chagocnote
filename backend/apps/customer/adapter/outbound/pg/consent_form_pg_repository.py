from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.consent_orm import CustomerFormOrm, CustomerFormPetOrm
from customer.app.ports.output.consent_form_repository import ConsentFormRepository
from customer.domain.entities.consent_form import ConsentForm
from customer.domain.errors import FormNotFoundError
from hub.app.dtos.shop_context import ShopContext

_KIND = "consent"


class ConsentFormPgRepository(ConsentFormRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...], public_id: bytes,
        expires_at: datetime,
    ) -> ConsentForm:
        form_id = (
            await self._session.execute(
                insert(CustomerFormOrm).values(
                    shop_id=ctx.shop_id, kind=_KIND, public_id=public_id, customer_id=customer_id,
                    expires_at=expires_at, created_by_member_id=ctx.member_id,
                ).returning(CustomerFormOrm.id)
            )
        ).scalar_one()
        await self._write_pets(form_id, pet_ids)
        return await self.get(ctx, form_id)

    async def live_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> list[ConsentForm]:
        rows = (
            await self._session.execute(
                self._live(ctx, now).where(CustomerFormOrm.customer_id == customer_id)
                .order_by(CustomerFormOrm.id).with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        return await self._forms(rows)

    async def list_live(self, ctx: ShopContext, now: datetime) -> list[ConsentForm]:
        rows = (
            await self._session.execute(
                self._live(ctx, now).order_by(CustomerFormOrm.created_at.desc(), CustomerFormOrm.id.desc())
            )
        ).scalars().all()
        return await self._forms(rows)

    async def get(self, ctx: ShopContext, form_id: int) -> ConsentForm:
        row = (
            await self._session.execute(
                select(CustomerFormOrm).where(
                    CustomerFormOrm.id == form_id, CustomerFormOrm.shop_id == ctx.shop_id,
                    CustomerFormOrm.kind == _KIND,
                ).execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise FormNotFoundError("서류를 찾을 수 없습니다.")
        return (await self._forms([row]))[0]

    async def revoke(self, ctx: ShopContext, form_id: int, now: datetime) -> None:
        await self._session.execute(
            update(CustomerFormOrm)
            .where(CustomerFormOrm.id == form_id, CustomerFormOrm.shop_id == ctx.shop_id,
                   CustomerFormOrm.revoked_at.is_(None), CustomerFormOrm.submitted_at.is_(None))
            .values(revoked_at=now)
        )

    async def set_pets(self, ctx: ShopContext, form_id: int, pet_ids: tuple[int, ...]) -> None:
        owned = select(CustomerFormOrm.id).where(
            CustomerFormOrm.id == form_id, CustomerFormOrm.shop_id == ctx.shop_id)
        await self._session.execute(delete(CustomerFormPetOrm).where(CustomerFormPetOrm.form_id.in_(owned)))
        if (await self._session.execute(owned)).scalar_one_or_none() is not None:
            await self._write_pets(form_id, pet_ids)

    async def sent_on(self, ctx: ShopContext, pet_ids: tuple[int, ...], now: datetime) -> dict[int, datetime]:
        if not pet_ids:
            return {}
        live = self._live(ctx, now).with_only_columns(CustomerFormOrm.id, CustomerFormOrm.created_at).subquery()
        rows = await self._session.execute(
            select(CustomerFormPetOrm.pet_id, func.max(live.c.created_at))
            .join(live, live.c.id == CustomerFormPetOrm.form_id)
            .where(CustomerFormPetOrm.pet_id.in_(pet_ids))
            .group_by(CustomerFormPetOrm.pet_id)
        )
        return {pet_id: sent_at for pet_id, sent_at in rows}

    async def find_public(self, public_id: bytes) -> ConsentForm | None:
        row = (
            await self._session.execute(
                select(CustomerFormOrm).where(
                    CustomerFormOrm.public_id == public_id, CustomerFormOrm.kind == _KIND
                ).execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return None if row is None else (await self._forms([row]))[0]

    async def lock(self, form_id: int) -> ConsentForm | None:
        row = (
            await self._session.execute(
                select(CustomerFormOrm).where(CustomerFormOrm.id == form_id, CustomerFormOrm.kind == _KIND)
                .with_for_update().execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return None if row is None else (await self._forms([row]))[0]

    async def mark_submitted(self, form_id: int, now: datetime) -> None:
        await self._session.execute(
            update(CustomerFormOrm)
            .where(CustomerFormOrm.id == form_id, CustomerFormOrm.submitted_at.is_(None))
            .values(submitted_at=now)
        )

    @staticmethod
    def _live(ctx: ShopContext, now: datetime):
        return select(CustomerFormOrm).where(
            CustomerFormOrm.shop_id == ctx.shop_id, CustomerFormOrm.kind == _KIND,
            CustomerFormOrm.revoked_at.is_(None), CustomerFormOrm.submitted_at.is_(None),
            CustomerFormOrm.expires_at > now,
        )

    async def _write_pets(self, form_id: int, pet_ids: tuple[int, ...]) -> None:
        if pet_ids:
            await self._session.execute(
                insert(CustomerFormPetOrm), [{"form_id": form_id, "pet_id": pet_id} for pet_id in sorted(set(pet_ids))]
            )

    async def _forms(self, rows) -> list[ConsentForm]:
        if not rows:
            return []
        pets: dict[int, list[int]] = {row.id: [] for row in rows}
        for form_id, pet_id in await self._session.execute(
            select(CustomerFormPetOrm.form_id, CustomerFormPetOrm.pet_id)
            .where(CustomerFormPetOrm.form_id.in_(pets)).order_by(CustomerFormPetOrm.pet_id)
        ):
            pets[form_id].append(pet_id)
        return [
            ConsentForm(
                id=row.id, shop_id=row.shop_id, public_id=bytes(row.public_id), customer_id=row.customer_id,
                pet_ids=tuple(pets[row.id]), expires_at=row.expires_at, revoked_at=row.revoked_at,
                submitted_at=row.submitted_at, created_by_member_id=row.created_by_member_id,
                created_at=row.created_at,
            )
            for row in rows
        ]
