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
    review_url: str | None = None    # 알림장 끝의 리뷰 남기기 줄(⑫) — 없으면 줄이 없다
    review_text: str | None = None   # 그 줄의 문구 — 없으면 기본 문구


DEFAULT_REPORT_SETTINGS = ReportSettings(
    link_days=30, show_menus=True, show_shop_info=True, show_weight=False, show_amount=False,
)
