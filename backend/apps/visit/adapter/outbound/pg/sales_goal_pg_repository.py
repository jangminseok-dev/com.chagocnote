from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.orm.visit_orm import VisitShopSettingsOrm
from visit.app.ports.output.sales_goal_repository import SalesGoalRepository


class SalesGoalPgRepository(SalesGoalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> int | None:
        return (
            await self._session.execute(
                select(VisitShopSettingsOrm.sales_monthly_goal).where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
            )
        ).scalar_one_or_none()

    async def put(self, ctx: ShopContext, monthly_amount: int | None) -> int | None:
        return (
            await self._session.execute(
                update(VisitShopSettingsOrm)
                .where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
                .values(sales_monthly_goal=monthly_amount)
                .returning(VisitShopSettingsOrm.sales_monthly_goal)
            )
        ).scalar_one()
