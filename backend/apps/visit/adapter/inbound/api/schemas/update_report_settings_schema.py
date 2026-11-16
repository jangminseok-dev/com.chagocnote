from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, StrictBool, StringConstraints

from visit.domain.services.report_rules import normalized_review_url
from visit.domain.value_objects.report_settings import ReportSettings


class UpdateReportSettingsRequestSchema(BaseModel):
    """다섯 칸 모두 필수다(전체 교체). 무기한은 link_days 에 null 을 적어 보낸다."""

    link_days: Literal[7, 30] | None
    show_menus: StrictBool
    show_shop_info: StrictBool
    show_weight: StrictBool
    show_amount: StrictBool
    # 리뷰 남기기 줄(⑫) — 칸을 보내지 않으면 지금 값을 둔다(이 칸을 모르는 예전 앱이 지우지 않게). null 은 지운다.
    # 길이 상한은 입력 경계다 — 규칙(300·60자, https 등)은 도메인이 본다.
    review_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    review_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None

    def kept(self) -> frozenset[str]:
        return frozenset(name for name in ("review_url", "review_text") if name not in self.model_fields_set)

    def to_settings(self) -> ReportSettings:
        return ReportSettings(
            link_days=self.link_days, show_menus=self.show_menus, show_shop_info=self.show_shop_info,
            show_weight=self.show_weight, show_amount=self.show_amount,
            review_url=normalized_review_url(self.review_url or None), review_text=self.review_text or None,
        )
