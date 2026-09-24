from __future__ import annotations

from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_record_mapper import to_record
from visit.adapter.outbound.orm.visit_orm import VisitOrm, VisitRecordItemOrm, VisitRecordMediaOrm, VisitRecordOrm
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.domain.entities.visit_record import VisitRecord


class VisitRecordPgRepository(VisitRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext, visit_id: int) -> VisitRecord | None:
        row = (
            await self._session.execute(
                select(VisitRecordOrm)
                .join(VisitOrm, VisitOrm.id == VisitRecordOrm.visit_id)
                .where(VisitRecordOrm.visit_id == visit_id, VisitOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return await self._assemble(row) if row is not None else None

    async def _assemble(self, row: VisitRecordOrm) -> VisitRecord:
        visit_id = row.visit_id
        items = (
            await self._session.execute(
                select(VisitRecordItemOrm).where(VisitRecordItemOrm.visit_id == visit_id)
                .order_by(VisitRecordItemOrm.menu_id).execution_options(populate_existing=True)
            )
        ).scalars().all()
        media = (
            await self._session.execute(
                select(VisitRecordMediaOrm).where(VisitRecordMediaOrm.visit_id == visit_id)
                .order_by(VisitRecordMediaOrm.phase.desc(), VisitRecordMediaOrm.sort_order)   # before → after
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        return to_record(row, list(items), list(media))

    async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
        fields = dict(
            weight_kg=record.weight_kg, care_note=record.care_note, internal_note=record.internal_note,
            payment_method=record.payment_method, total_amount=record.total_amount, version=record.version,
            updated_by_member_id=record.updated_by_member_id,
        )
        await self._session.execute(
            pg_insert(VisitRecordOrm)
            .values(visit_id=record.visit_id, created_by_member_id=record.created_by_member_id, **fields)
            .on_conflict_do_update(index_elements=[VisitRecordOrm.visit_id], set_={**fields, "updated_at": func.now()})
        )
        await self._session.execute(delete(VisitRecordItemOrm).where(VisitRecordItemOrm.visit_id == record.visit_id))
        await self._session.execute(delete(VisitRecordMediaOrm).where(VisitRecordMediaOrm.visit_id == record.visit_id))
        if record.items:
            await self._session.execute(
                insert(VisitRecordItemOrm),
                [dict(visit_id=record.visit_id, menu_id=i.menu_id, amount=i.amount) for i in record.items],
            )
        if record.media:
            await self._session.execute(
                insert(VisitRecordMediaOrm),
                [dict(visit_id=record.visit_id, media_id=m.media_id, kind=m.kind, phase=m.phase,
                      sort_order=m.sort_order) for m in record.media],
            )
        row = (
            await self._session.execute(
                select(VisitRecordOrm).where(VisitRecordOrm.visit_id == record.visit_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return await self._assemble(row)
