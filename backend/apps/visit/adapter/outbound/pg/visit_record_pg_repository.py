from __future__ import annotations

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_record_mapper import to_record
from visit.adapter.outbound.orm.visit_orm import VisitOrm, VisitRecordItemOrm, VisitRecordMediaOrm, VisitRecordOrm
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.domain.entities.visit import COMPLETED
from visit.domain.entities.visit_record import VisitRecord


class VisitRecordPgRepository(VisitRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext, visit_id: int) -> VisitRecord | None:
        return (await self.list_many(ctx, [visit_id])).get(visit_id)

    async def list_many(self, ctx: ShopContext, visit_ids: list[int]) -> dict[int, VisitRecord]:
        if not visit_ids:
            return {}
        rows = (
            await self._session.execute(
                select(VisitRecordOrm)
                .join(VisitOrm, VisitOrm.id == VisitRecordOrm.visit_id)
                .where(VisitRecordOrm.visit_id.in_(visit_ids), VisitOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        return await self._assemble(rows)

    async def _assemble(self, rows) -> dict[int, VisitRecord]:
        """기록 행들에 항목·미디어를 한 번씩 읽어 붙인다(방문 수만큼 묻지 않는다)."""
        ids = [row.visit_id for row in rows]
        items: dict[int, list[VisitRecordItemOrm]] = {i: [] for i in ids}
        media: dict[int, list[VisitRecordMediaOrm]] = {i: [] for i in ids}
        if ids:
            for item in (await self._session.execute(
                select(VisitRecordItemOrm).where(VisitRecordItemOrm.visit_id.in_(ids))
                .order_by(VisitRecordItemOrm.visit_id, VisitRecordItemOrm.menu_id)
                .execution_options(populate_existing=True)
            )).scalars():
                items[item.visit_id].append(item)
            for m in (await self._session.execute(
                select(VisitRecordMediaOrm).where(VisitRecordMediaOrm.visit_id.in_(ids))
                .order_by(VisitRecordMediaOrm.visit_id, VisitRecordMediaOrm.phase.desc(),   # before → after
                          VisitRecordMediaOrm.sort_order)
                .execution_options(populate_existing=True)
            )).scalars():
                media[m.visit_id].append(m)
        return {row.visit_id: to_record(row, items[row.visit_id], media[row.visit_id]) for row in rows}

    async def latest_with_media(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
        if not pet_ids:
            return {}
        rows = await self._session.execute(
            select(VisitOrm.pet_id, VisitOrm.id)
            .distinct(VisitOrm.pet_id)
            .where(
                VisitOrm.shop_id == ctx.shop_id, VisitOrm.pet_id.in_(pet_ids), VisitOrm.status == COMPLETED,
                VisitOrm.id.in_(select(VisitRecordMediaOrm.visit_id)),
            )
            .order_by(VisitOrm.pet_id, VisitOrm.starts_at.desc(), VisitOrm.id.desc())
        )
        return dict(rows.all())

    async def clear_notes(self, ctx: ShopContext, customer_id: int) -> None:
        await self._session.execute(
            update(VisitRecordOrm)
            .where(VisitRecordOrm.visit_id.in_(
                select(VisitOrm.id).where(VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id)
            ))
            .values(care_note=None, internal_note=None)
        )

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
                      sort_order=m.sort_order, hidden_from_report=m.hidden) for m in record.media],
            )
        row = (
            await self._session.execute(
                select(VisitRecordOrm).where(VisitRecordOrm.visit_id == record.visit_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return (await self._assemble([row]))[record.visit_id]

    async def set_hidden(self, ctx: ShopContext, visit_id: int, hidden_ids: tuple[int, ...]) -> None:
        await self._session.execute(
            update(VisitRecordMediaOrm)
            .where(VisitRecordMediaOrm.visit_id == visit_id)
            .values(hidden_from_report=VisitRecordMediaOrm.media_id.in_(hidden_ids))
        )

    async def delete(self, ctx: ShopContext, visit_id: int) -> None:
        await self._session.execute(delete(VisitRecordOrm).where(VisitRecordOrm.visit_id == visit_id))
