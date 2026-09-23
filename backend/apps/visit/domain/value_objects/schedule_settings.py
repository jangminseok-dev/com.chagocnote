from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class ScheduleSettings:
    """매장 일정 설정 — 영업시간 하나, 기본 소요, 매주 쉬는 요일(월=0 … 일=6)."""

    opens_at: time
    closes_at: time
    default_duration_minutes: int
    closed_weekdays: frozenset[int]


DEFAULT_SETTINGS = ScheduleSettings(
    opens_at=time(10, 0), closes_at=time(19, 0), default_duration_minutes=120,
    closed_weekdays=frozenset(),
)

# 매장을 처음 쓸 때 넣는 메뉴(이름, 기본 소요). 첫 짐작이고 사장이 바꾼다.
DEFAULT_MENUS: tuple[tuple[str, int], ...] = (
    ("목욕", 60), ("위생", 60), ("부분 미용", 90), ("전체 미용", 150), ("스포팅", 120),
)
