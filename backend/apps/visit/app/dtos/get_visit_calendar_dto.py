from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetVisitCalendarQuery:
    ctx: ShopContext
    year: int
    month: int


@dataclass(frozen=True)
class CalendarDayView:
    date: date
    visit_count: int       # 마릿수 — 예약됨·미용 중·완료
    completed_count: int
    open_count: int        # 예약됨·미용 중
    unresolved_count: int  # 지난 날인데 아직 예약됨
    closed_day: bool


@dataclass(frozen=True)
class VisitCalendarView:
    year: int
    month: int
    days: list[CalendarDayView]            # 그달의 모든 날
    unresolved_total: int                  # 달과 상관없이 매장 전체
    oldest_unresolved_date: date | None
