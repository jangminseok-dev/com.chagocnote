from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_mapper import to_visit
from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import ACTIVE_STATUSES, RESERVED, Visit
from visit.domain.errors import VisitDuplicateError
from visit.domain.services.visit_schedule import MAX_DURATION
from visit.domain.value_objects.new_visit import NewVisit

_DUPLICATE = {"uq_visits_pet_start_active", "uq_visits_customer_start_active"}


class VisitPgRepository(VisitRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, ctx: ShopContext, visits: list[NewVisit]) -> list[Visit]:
        async with self._duplicate_guard():
            ids = []
            for new in visits:
                visit_id = (
                    await self._session.execute(
                        insert(VisitOrm)
                        .values(
                            shop_id=ctx.shop_id, customer_id=new.customer_id, pet_id=new.pet_id,
                            starts_at=new.starts_at, duration_minutes=new.duration_minutes,
                            status=new.status, started_at=new.started_at, memo=new.memo,
                            created_by_member_id=new.created_by_member_id,
                            status_changed_by_member_id=(
                                new.created_by_member_id if new.started_at is not None else None
                            ),
                        )
                        .returning(VisitOrm.id)
                    )
                ).scalar_one()
                if new.menu_ids:
                    await self._session.execute(
                        insert(VisitMenuOrm), [dict(visit_id=visit_id, menu_id=m) for m in new.menu_ids]
                    )
                ids.append(visit_id)
        return await self._read(ctx, select(VisitOrm).where(VisitOrm.id.in_(ids)))

    async def list_between(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        return await self._read(
            ctx, select(VisitOrm).where(VisitOrm.starts_at >= start, VisitOrm.starts_at < end)
        )

    async def unresolved_before(self, ctx: ShopContext, before: datetime) -> tuple[int, datetime | None]:
        count, oldest = (
            await self._session.execute(
                select(func.count(), func.min(VisitOrm.starts_at)).where(
                    VisitOrm.shop_id == ctx.shop_id, VisitOrm.status == RESERVED,
                    VisitOrm.starts_at < before,
                )
            )
        ).one()
        return count, oldest

    async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        # 소요는 최대 600분이라 그만큼 앞에서 시작한 방문까지 가져와 끝 시각으로 거른다.
        rows = await self._read(
            ctx,
            select(VisitOrm).where(
                VisitOrm.status.in_(ACTIVE_STATUSES),
                VisitOrm.starts_at >= start - timedelta(minutes=MAX_DURATION),
                VisitOrm.starts_at < end,
            ),
        )
        return [v for v in rows if v.ends_at > start]

    async def _read(self, ctx: ShopContext, stmt) -> list[Visit]:
        rows = (
            await self._session.execute(
                stmt.where(VisitOrm.shop_id == ctx.shop_id)
                .order_by(VisitOrm.starts_at, VisitOrm.id)
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        menus: dict[int, list[int]] = {}
        if rows:
            pairs = await self._session.execute(
                select(VisitMenuOrm.visit_id, VisitMenuOrm.menu_id)
                .where(VisitMenuOrm.visit_id.in_([r.id for r in rows]))
                .order_by(VisitMenuOrm.visit_id, VisitMenuOrm.menu_id)
            )
            for visit_id, menu_id in pairs:
                menus.setdefault(visit_id, []).append(menu_id)
        return [to_visit(row, menus.get(row.id, [])) for row in rows]

    @asynccontextmanager
    async def _duplicate_guard(self):
        """중복 예약 유일 색인 위반을 VISIT_DUPLICATE 로 바꾼다. 세이브포인트라 트랜잭션은 계속 쓸 수 있다.

        같은 예약을 동시에 넣는 두 요청 중 늦은 쪽은 앞선 쪽이 커밋할 때까지 색인에서 기다렸다가 여기서 걸린다.
        """
        try:
            async with self._session.begin_nested():
                yield
        except IntegrityError as exc:
            if getattr(exc.orig.__cause__, "constraint_name", None) in _DUPLICATE:
                raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.") from exc
            raise
