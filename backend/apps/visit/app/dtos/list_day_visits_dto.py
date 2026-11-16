from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
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
    # 남은 일(⑬ 설계 3.5) — 하루 머리의 숫자. 지난 날·오늘만 0 이 아니다. 금액이 아니라 수다.
    unpaid: int = 0          # 완료했고 결제 완료가 아니다
    report_unsent: int = 0   # 완료했고 기록이 있는데 알림장을 보낸 적도 넘긴 적도 없다(매장이 세기로 했을 때)
    checks: int = 0          # 확인할 것이 있는 살아 있는 방문의 수

    @classmethod
    def of(cls, counts: Mapping[str, int], **extra: int) -> DayCountsView:
        """상태 이름 → 수 매핑에서 만든다. 어느 칸이 상태인지는 필드 이름으로 안다 — 마릿수와 extra 로 주는 칸
        (정리 안 됨·남은 일·확인할 것)은 아니다."""
        status_fields = [f.name for f in fields(cls) if f.name not in ("visit_count", *_NOT_STATUS)]
        return cls(
            visit_count=sum(counts.get(s, 0) for s in COUNTED_STATUSES),
            **{name: extra.get(name, 0) for name in _NOT_STATUS},
            **{name: counts.get(name, 0) for name in status_fields},
        )


_NOT_STATUS = ("unresolved", "unpaid", "report_unsent", "checks")


@dataclass(frozen=True)
class DayVisitItemView:
    visit: VisitView
    group_key: str      # 가족 묶음 — 같은 값끼리 한 카드로 묶는다
    overlapping: bool   # 다른 묶음과 시간이 겹친다
    unresolved: bool    # 지난 날인데 아직 예약됨
    has_record: bool    # 미용 기록이 있다
    cover: str | None   # 대표 사진 썸네일
    report_sent: bool   # 살아 있는 알림장 링크가 있다
    # 확인할 것의 수(③-B) — 지병은 세지 않는다. 가족 묶음에서 보호자 항목은 한 번만 세라고 둘로 나눠 준다.
    customer_check_count: int = 0
    pet_check_count: int = 0
    marks: list[str] = field(default_factory=list)   # 끝낸 일의 낱말 코드(⑬ 4.4) — paid · report_sent 차례


@dataclass(frozen=True)
class DayVisitsView:
    date: date
    closed_day: bool
    counts: DayCountsView
    items: list[DayVisitItemView]
