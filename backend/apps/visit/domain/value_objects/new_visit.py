from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewVisit:
    """새로 넣을 방문 하나. 예약이면 reserved, 지금 시작한 손님이면 in_progress 로 들어간다."""

    customer_id: int
    pet_id: int | None
    starts_at: datetime
    duration_minutes: int
    status: str
    started_at: datetime | None
    menu_ids: tuple[int, ...]
    memo: str | None
    created_by_member_id: int
