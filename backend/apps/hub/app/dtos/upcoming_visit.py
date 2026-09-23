from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UpcomingVisit:
    """다가오는 예약 한 건(고객 상세에 보여 줄 것). pet_id 가 None 이면 보호자만의 방문이다."""

    visit_id: int
    pet_id: int | None
    starts_at: datetime
