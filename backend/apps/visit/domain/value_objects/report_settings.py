from __future__ import annotations

from dataclasses import dataclass

LINK_DAYS = (7, 30)   # 고를 수 있는 링크 기간(일). 이 밖에는 무기한(None)뿐이다


@dataclass(frozen=True)
class ReportSettings:
    """매장의 알림장 설정 — 링크 기간과 보호자에게 함께 보여 줄 항목(설계 4.3)."""

    link_days: int | None     # None 이면 무기한
    show_menus: bool
    show_shop_info: bool
    show_weight: bool
    show_amount: bool


DEFAULT_REPORT_SETTINGS = ReportSettings(
    link_days=30, show_menus=True, show_shop_info=True, show_weight=False, show_amount=False,
)
