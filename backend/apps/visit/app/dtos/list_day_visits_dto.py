from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class ListDayVisitsQuery:
    ctx: ShopContext
    day: date   # 매장 시간대의 날짜


@dataclass(frozen=True)
class DayCountsView:
    visit_count: int   # 마릿수 — 예약됨·미용 중·완료
    reserved: int
    in_progress: int
    completed: int
    canceled: int
    no_show: int
    unresolved: int


@dataclass(frozen=True)
class DayVisitItemView:
    visit: VisitView
    group_key: str      # 가족 묶음 — 같은 값끼리 한 카드로 묶는다
    overlapping: bool   # 다른 묶음과 시간이 겹친다
    unresolved: bool    # 지난 날인데 아직 예약됨


@dataclass(frozen=True)
class DayVisitsView:
    date: date
    closed_day: bool
    counts: DayCountsView
    items: list[DayVisitItemView]
