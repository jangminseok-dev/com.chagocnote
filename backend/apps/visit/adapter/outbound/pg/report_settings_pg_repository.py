from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.orm.visit_orm import VisitShopSettingsOrm
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings

# ReportSettings 의 필드 순서와 같다.
_COLUMNS = (
    VisitShopSettingsOrm.report_link_days,
    VisitShopSettingsOrm.report_show_menus,
    VisitShopSettingsOrm.report_show_shop_info,
    VisitShopSettingsOrm.report_show_weight,
    VisitShopSettingsOrm.report_show_amount,
    VisitShopSettingsOrm.report_review_url,
    VisitShopSettingsOrm.report_review_text,
)


class ReportSettingsPgRepository(ReportSettingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, ctx: ShopContext) -> ReportSettings:
        row = (
            await self._session.execute(
                select(*_COLUMNS).where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
            )
        ).one_or_none()
        return DEFAULT_REPORT_SETTINGS if row is None else ReportSettings(*row)

    async def update(self, ctx: ShopContext, settings: ReportSettings) -> ReportSettings:
        row = (
            await self._session.execute(
                update(VisitShopSettingsOrm)
                .where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
                .values(
                    report_link_days=settings.link_days,
                    report_show_menus=settings.show_menus,
                    report_show_shop_info=settings.show_shop_info,
                    report_show_weight=settings.show_weight,
                    report_show_amount=settings.show_amount,
                    report_review_url=settings.review_url,
                    report_review_text=settings.review_text,
                )
                .returning(*_COLUMNS)
            )
        ).one()
        return ReportSettings(*row)
