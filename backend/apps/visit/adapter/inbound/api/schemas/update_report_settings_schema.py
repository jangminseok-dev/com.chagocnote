from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, StrictBool

from visit.domain.value_objects.report_settings import ReportSettings


class UpdateReportSettingsRequestSchema(BaseModel):
    """다섯 칸 모두 필수다(전체 교체). 무기한은 link_days 에 null 을 적어 보낸다."""

    link_days: Literal[7, 30] | None
    show_menus: StrictBool
    show_shop_info: StrictBool
    show_weight: StrictBool
    show_amount: StrictBool

    def to_settings(self) -> ReportSettings:
        return ReportSettings(
            link_days=self.link_days, show_menus=self.show_menus, show_shop_info=self.show_shop_info,
            show_weight=self.show_weight, show_amount=self.show_amount,
        )
