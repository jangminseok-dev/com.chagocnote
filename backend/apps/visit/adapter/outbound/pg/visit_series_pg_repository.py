from __future__ import annotations

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.orm.visit_orm import VisitSeriesOrm
from visit.app.ports.output.visit_series_repository import VisitSeriesRepository
from visit.domain.entities.visit_series import VisitSeries
from visit.domain.errors import VisitSeriesNotFoundError


def _to_series(row: VisitSeriesOrm) -> VisitSeries:
    return VisitSeries(id=row.id, shop_id=row.shop_id, customer_id=row.customer_id,
                       interval_weeks=row.interval_weeks, created_by_member_id=row.created_by_member_id,
                       created_at=row.created_at)


class VisitSeriesPgRepository(VisitSeriesRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, ctx: ShopContext, customer_id: int, interval_weeks: int, member_id: int) -> VisitSeries:
        row = (
            await self._session.execute(
                insert(VisitSeriesOrm)
                .values(shop_id=ctx.shop_id, customer_id=customer_id, interval_weeks=interval_weeks,
                        created_by_member_id=member_id)
                .returning(VisitSeriesOrm)
            )
        ).scalar_one()
        return _to_series(row)

    async def get(self, ctx: ShopContext, series_id: int) -> VisitSeries:
        row = (
            await self._session.execute(
                select(VisitSeriesOrm).where(VisitSeriesOrm.id == series_id, VisitSeriesOrm.shop_id == ctx.shop_id)
            )
        ).scalar_one_or_none()
        if row is None:
            raise VisitSeriesNotFoundError("반복 예약 묶음을 찾을 수 없습니다.")
        return _to_series(row)
