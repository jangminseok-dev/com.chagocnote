from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VisitSeries:
    """한꺼번에 잡은 반복 예약의 묶음(⑭ 설계 3.7). 간격은 보여 주려고만 남긴다 — 규칙으로 예약을 만들어 내지 않는다."""

    id: int
    shop_id: int
    customer_id: int
    interval_weeks: int
    created_by_member_id: int
    created_at: datetime
