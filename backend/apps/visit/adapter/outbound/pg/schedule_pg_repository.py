from __future__ import annotations

from datetime import date

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.orm.visit_orm import (
    ServiceMenuOrm,
    VisitClosedDateOrm,
    VisitShopSettingsOrm,
    VisitWeeklyClosureOrm,
)
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import DEFAULT_MENUS, DEFAULT_SETTINGS, ScheduleSettings


class SchedulePgRepository(ScheduleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure(self, ctx: ShopContext) -> ScheduleSettings:
        # 동시에 처음 쓰는 두 요청 중 늦은 쪽은 앞선 쪽의 커밋까지 여기서 기다렸다가 DO NOTHING 이 된다.
        created = (
            await self._session.execute(
                pg_insert(VisitShopSettingsOrm)
                .values(
                    shop_id=ctx.shop_id,
                    opens_at=DEFAULT_SETTINGS.opens_at,
                    closes_at=DEFAULT_SETTINGS.closes_at,
                    default_duration_minutes=DEFAULT_SETTINGS.default_duration_minutes,
                )
                .on_conflict_do_nothing(index_elements=[VisitShopSettingsOrm.shop_id])
                .returning(VisitShopSettingsOrm.shop_id)
            )
        ).scalar_one_or_none()
        if created is not None:
            await self._session.execute(
                insert(ServiceMenuOrm),
                [
                    dict(shop_id=ctx.shop_id, name=name, default_duration_minutes=minutes, sort_order=order)
                    for order, (name, minutes) in enumerate(DEFAULT_MENUS, start=1)
                ],
            )
        return await self._read(ctx)

    async def update(self, ctx: ShopContext, settings: ScheduleSettings) -> ScheduleSettings:
        # 설정 행 UPDATE 를 맨 먼저 한다 — 두 사장이 동시에 바꾸면 늦은 쪽이 이 행에서 기다렸다가, 앞선 쪽이
        # 커밋한 쉬는 요일을 보고 지우고 넣는다(지우고 넣기가 섞여 기본 키가 부딪히지 않는다).
        await self._session.execute(
            update(VisitShopSettingsOrm)
            .where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
            .values(opens_at=settings.opens_at, closes_at=settings.closes_at,
                    default_duration_minutes=settings.default_duration_minutes)
        )
        await self._session.execute(
            delete(VisitWeeklyClosureOrm).where(VisitWeeklyClosureOrm.shop_id == ctx.shop_id)
        )
        if settings.closed_weekdays:
            await self._session.execute(
                insert(VisitWeeklyClosureOrm),
                [dict(shop_id=ctx.shop_id, weekday=d) for d in sorted(settings.closed_weekdays)],
            )
        return await self._read(ctx)

    async def list_closed_dates(self, ctx: ShopContext, start: date, end: date) -> list[ClosedDate]:
        rows = (
            await self._session.execute(
                select(VisitClosedDateOrm)
                .where(VisitClosedDateOrm.shop_id == ctx.shop_id,
                       VisitClosedDateOrm.day.between(start, end))
                .order_by(VisitClosedDateOrm.day)
            )
        ).scalars()
        return [ClosedDate(day=row.day, note=row.note) for row in rows]

    async def add_closed_date(self, ctx: ShopContext, day: date, note: str | None) -> ClosedDate:
        await self._session.execute(
            pg_insert(VisitClosedDateOrm)
            .values(shop_id=ctx.shop_id, day=day, note=note)
            .on_conflict_do_nothing(index_elements=[VisitClosedDateOrm.shop_id, VisitClosedDateOrm.day])
        )
        [found] = await self.list_closed_dates(ctx, day, day)
        return found

    async def delete_closed_date(self, ctx: ShopContext, day: date) -> None:
        await self._session.execute(
            delete(VisitClosedDateOrm).where(
                VisitClosedDateOrm.shop_id == ctx.shop_id, VisitClosedDateOrm.day == day
            )
        )

    async def _read(self, ctx: ShopContext) -> ScheduleSettings:
        row = (
            await self._session.execute(
                select(VisitShopSettingsOrm)
                .where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        weekdays = (
            await self._session.execute(
                select(VisitWeeklyClosureOrm.weekday).where(VisitWeeklyClosureOrm.shop_id == ctx.shop_id)
            )
        ).scalars()
        return ScheduleSettings(
            opens_at=row.opens_at, closes_at=row.closes_at,
            default_duration_minutes=row.default_duration_minutes, closed_weekdays=frozenset(weekdays),
        )
