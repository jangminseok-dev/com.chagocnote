from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_mapper import to_visit
from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import ACTIVE_STATUSES, COMPLETED, NO_SHOW, RESERVED, Visit
from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
from visit.domain.services.visit_schedule import MAX_DURATION
from visit.domain.state.visit_state import StatusChange
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

    async def get(self, ctx: ShopContext, visit_id: int) -> Visit:
        found = await self._read(ctx, select(VisitOrm).where(VisitOrm.id == visit_id))
        if not found:
            raise VisitNotFoundError("방문을 찾을 수 없습니다.")
        return found[0]

    async def get_many(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
        return await self._read(ctx, select(VisitOrm).where(VisitOrm.id.in_(visit_ids)))

    async def lock(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
        # ID 오름차순으로 잠근다 — 가족 묶음을 서로 다른 순서로 잠그는 두 요청이 교착에 빠지지 않는다.
        await self._session.execute(
            select(VisitOrm.id)
            .where(VisitOrm.id.in_(visit_ids), VisitOrm.shop_id == ctx.shop_id)
            .order_by(VisitOrm.id)
            .with_for_update()
        )
        return await self.get_many(ctx, visit_ids)

    async def update_details(
        self, ctx: ShopContext, visit_id: int, starts_at: datetime, pet_id: int | None,
        duration_minutes: int, menu_ids: tuple[int, ...], memo: str | None,
    ) -> Visit:
        async with self._duplicate_guard():
            await self._session.execute(
                update(VisitOrm)
                .where(VisitOrm.id == visit_id, VisitOrm.shop_id == ctx.shop_id)
                .values(starts_at=starts_at, pet_id=pet_id, duration_minutes=duration_minutes, memo=memo)
            )
        await self._session.execute(delete(VisitMenuOrm).where(VisitMenuOrm.visit_id == visit_id))
        if menu_ids:
            await self._session.execute(
                insert(VisitMenuOrm), [dict(visit_id=visit_id, menu_id=m) for m in menu_ids]
            )
        return await self.get(ctx, visit_id)

    async def reschedule(self, ctx: ShopContext, visit_ids: list[int], starts_at: datetime) -> list[Visit]:
        async with self._duplicate_guard():
            await self._session.execute(
                update(VisitOrm)
                .where(VisitOrm.id.in_(visit_ids), VisitOrm.shop_id == ctx.shop_id)
                .values(starts_at=starts_at)
            )
        return await self.get_many(ctx, visit_ids)

    async def apply_changes(
        self, ctx: ShopContext, changes: list[tuple[int, StatusChange]], member_id: int
    ) -> list[Visit]:
        async with self._duplicate_guard():
            for visit_id, change in changes:
                await self._session.execute(
                    update(VisitOrm)
                    .where(VisitOrm.id == visit_id, VisitOrm.shop_id == ctx.shop_id)
                    .values(status=change.status, started_at=change.started_at,
                            completed_at=change.completed_at, canceled_at=change.canceled_at,
                            cancel_reason=change.cancel_reason, status_changed_by_member_id=member_id)
                )
        return await self.get_many(ctx, [visit_id for visit_id, _ in changes])

    async def latest_completed_start(self, ctx: ShopContext, customer_id: int) -> datetime | None:
        return (
            await self._session.execute(
                select(func.max(VisitOrm.starts_at)).where(
                    VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id,
                    VisitOrm.status == COMPLETED,
                )
            )
        ).scalar_one()

    async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
        return await self._read(
            ctx, select(VisitOrm).where(VisitOrm.customer_id == customer_id, VisitOrm.starts_at == starts_at)
        )

    async def last_completed_before(
        self, ctx: ShopContext, customer_id: int, pet_id: int | None, before: datetime
    ) -> Visit | None:
        whose = VisitOrm.pet_id == pet_id if pet_id is not None else VisitOrm.pet_id.is_(None)
        found = await self._read(
            ctx,
            select(VisitOrm)
            .where(VisitOrm.customer_id == customer_id, whose, VisitOrm.status == COMPLETED,
                   VisitOrm.starts_at < before)
            .order_by(VisitOrm.starts_at.desc())
            .limit(1),
        )
        return found[0] if found else None

    async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int:
        return (
            await self._session.execute(
                select(func.count()).where(
                    VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id,
                    VisitOrm.status == NO_SHOW,
                )
            )
        ).scalar_one()

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
