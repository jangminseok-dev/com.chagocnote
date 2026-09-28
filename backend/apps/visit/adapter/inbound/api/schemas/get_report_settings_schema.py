from __future__ import annotations

from pydantic import BaseModel

from visit.domain.value_objects.report_settings import ReportSettings


class ReportSettingsSchema(BaseModel):
    link_days: int | None   # 7·30, null 이면 무기한
    show_menus: bool
    show_shop_info: bool
    show_weight: bool
    show_amount: bool

    @classmethod
    def of(cls, settings: ReportSettings) -> ReportSettingsSchema:
        return cls(link_days=settings.link_days, show_menus=settings.show_menus,
                   show_shop_info=settings.show_shop_info, show_weight=settings.show_weight,
                   show_amount=settings.show_amount)
