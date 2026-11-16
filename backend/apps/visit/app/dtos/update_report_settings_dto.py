from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.report_settings import ReportSettings


@dataclass(frozen=True)
class UpdateReportSettingsCommand:
    """알림장 설정 전체를 바꾼다(PUT)."""

    ctx: ShopContext
    settings: ReportSettings
    kept: frozenset[str] = frozenset()   # 보내지 않은 칸 — 지금 값을 둔다(review_url·review_text)
