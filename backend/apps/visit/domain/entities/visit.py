from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

RESERVED = "reserved"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
CANCELED = "canceled"
NO_SHOW = "no_show"

# 살아 있는 방문 — 시간을 차지하고, 앞으로의 예약으로 센다.
ACTIVE_STATUSES = frozenset({RESERVED, IN_PROGRESS})

CANCEL_REASONS = frozenset({"customer_request", "shop_reason"})


@dataclass(frozen=True)
class Visit:
    """반려동물 한 마리(pet_id 가 None 이면 보호자만)의 방문 하나. 예약부터 완료까지 한 애그리거트다."""

    id: int
    shop_id: int
    customer_id: int
    pet_id: int | None
    starts_at: datetime
    duration_minutes: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    canceled_at: datetime | None
    cancel_reason: str | None
    memo: str | None
    menu_ids: tuple[int, ...]
    created_by_member_id: int
    status_changed_by_member_id: int | None

    @property
    def ends_at(self) -> datetime:
        return self.starts_at + timedelta(minutes=self.duration_minutes)

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def group_key(self) -> tuple[int, datetime]:
        """가족 묶음 — 같은 보호자 + 같은 시작 시각. 저장하지 않고 계산한다."""
        return (self.customer_id, self.starts_at)
