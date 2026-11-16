from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView

UNRESOLVED = "unresolved"
UNPAID = "unpaid"
REPORT_UNSENT = "report_unsent"


@dataclass(frozen=True)
class GetDayWrapUpQuery:
    ctx: ShopContext
    day: date


@dataclass(frozen=True)
class PrefillView:
    """결제 장에 채워 둘 값 — 둘 다 고칠 수 있고, 근거가 없으면 None(앱이 그 자리에서 묻는다)."""

    total_amount: int | None
    payment_method: str | None


@dataclass(frozen=True)
class WrapUpCardView:
    """하루 마무리의 한 장 — 방문 하나의 남은 일 하나(⑬ 설계 3.6)."""

    kind: str                       # unresolved · unpaid · report_unsent
    visit: VisitView
    photo_url: str | None           # 아이의 프로필 사진(사진이 붙은 가장 최근 완료 방문의 대표)
    prefill: PrefillView | None     # 결제 장에만


@dataclass(frozen=True)
class DayWrapUpView:
    date: date
    cards: list[WrapUpCardView]
