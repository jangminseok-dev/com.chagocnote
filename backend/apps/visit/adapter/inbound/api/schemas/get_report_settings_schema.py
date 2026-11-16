from __future__ import annotations

from pydantic import BaseModel

from visit.domain.services.report_rules import DEFAULT_REVIEW_TEXT
from visit.domain.value_objects.report_settings import ReportSettings


class ReportSettingsSchema(BaseModel):
    link_days: int | None   # 7·30, null 이면 무기한
    show_menus: bool
    show_shop_info: bool
    show_weight: bool
    show_amount: bool
    review_url: str | None           # 알림장 끝의 리뷰 남기기 줄(⑫) — 없으면 줄이 없다
    review_text: str | None          # 매장이 고친 문구 — 없으면 기본 문구가 나간다
    review_text_default: str = DEFAULT_REVIEW_TEXT   # 앱이 칸을 미리 채우고 기본으로 되돌릴 때 쓴다

    @classmethod
    def of(cls, settings: ReportSettings) -> ReportSettingsSchema:
        return cls(link_days=settings.link_days, show_menus=settings.show_menus,
                   show_shop_info=settings.show_shop_info, show_weight=settings.show_weight,
                   show_amount=settings.show_amount, review_url=settings.review_url,
                   review_text=settings.review_text)
