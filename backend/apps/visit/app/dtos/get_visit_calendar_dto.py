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
    cover: str | None      # 그날 완료 방문 가운데 시작 순 첫 대표 사진의 썸네일
    covers: list[str]      # 미리보기 카드용 — 같은 순서로 최대 4장


@dataclass(frozen=True)
class VisitCalendarView:
    year: int
    month: int
    days: list[CalendarDayView]            # 그달의 모든 날
    unresolved_total: int                  # 달과 상관없이 매장 전체
    oldest_unresolved_date: date | None
