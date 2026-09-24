from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView
from visit.domain.state.visit_status import COUNTED_STATUSES


@dataclass(frozen=True)
class ListDayVisitsQuery:
    ctx: ShopContext
    day: date   # 매장 시간대의 날짜


@dataclass(frozen=True)
class DayCountsView:
    """상태별 수. 상태 이름과 같은 칸이 하나씩 있다 — 상태가 늘면 칸을 더하고, `of`가 그것을 채운다."""

    visit_count: int   # 마릿수 — 예약됨·미용 중·완료
    reserved: int
    in_progress: int
    completed: int
    canceled: int
    no_show: int
    unresolved: int

    @classmethod
    def of(cls, counts: Mapping[str, int], unresolved: int) -> DayCountsView:
        """상태 이름 → 수 매핑에서 만든다. 어느 칸이 상태인지는 필드 이름으로 안다(visit_count·unresolved 는 아니다)."""
        status_fields = [f.name for f in fields(cls) if f.name not in ("visit_count", "unresolved")]
        return cls(
            visit_count=sum(counts.get(s, 0) for s in COUNTED_STATUSES),
            unresolved=unresolved,
            **{name: counts.get(name, 0) for name in status_fields},
        )


@dataclass(frozen=True)
class DayVisitItemView:
    visit: VisitView
    group_key: str      # 가족 묶음 — 같은 값끼리 한 카드로 묶는다
    overlapping: bool   # 다른 묶음과 시간이 겹친다
    unresolved: bool    # 지난 날인데 아직 예약됨
    has_record: bool    # 미용 기록이 있다
    cover: str | None   # 대표 사진 썸네일


@dataclass(frozen=True)
class DayVisitsView:
    date: date
    closed_day: bool
    counts: DayCountsView
    items: list[DayVisitItemView]
