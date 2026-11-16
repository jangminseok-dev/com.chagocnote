from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.orm.visit_orm import VisitShopSettingsOrm
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.domain.value_objects.revisit_settings import DEFAULT_REVISIT_SETTINGS, RevisitSettings

# RevisitSettings 의 필드 순서와 같다.
_COLUMNS = (
    VisitShopSettingsOrm.default_cycle_weeks,
    VisitShopSettingsOrm.revisit_soon_days,
    VisitShopSettingsOrm.revisit_message,
    VisitShopSettingsOrm.count_unsent_reports,
    VisitShopSettingsOrm.cycle_sample_visits,
    VisitShopSettingsOrm.cycle_min_gap_days,
)


class RevisitSettingsPgRepository(RevisitSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> RevisitSettings:
        row = (
            await self._session.execute(select(*_COLUMNS).where(VisitShopSettingsOrm.shop_id == ctx.shop_id))
        ).one_or_none()
        return DEFAULT_REVISIT_SETTINGS if row is None else RevisitSettings(*row)

    async def update(self, ctx: ShopContext, settings: RevisitSettings) -> RevisitSettings:
        row = (
            await self._session.execute(
                update(VisitShopSettingsOrm)
                .where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
                .values(
                    default_cycle_weeks=settings.default_cycle_weeks,
                    revisit_soon_days=settings.revisit_soon_days,
                    revisit_message=settings.revisit_message,
                    count_unsent_reports=settings.count_unsent_reports,
                    cycle_sample_visits=settings.cycle_sample_visits,
                    cycle_min_gap_days=settings.cycle_min_gap_days,
                )
                .returning(*_COLUMNS)
            )
        ).one()
        return RevisitSettings(*row)
