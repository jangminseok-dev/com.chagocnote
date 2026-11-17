from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# 상태 이름과 집합의 원천은 domain/state/visit_status.py 다. 여기서는 부르는 쪽의 편의로 다시 내보낸다.
from visit.domain.state.visit_status import (  # noqa: F401 — 다시 내보냄
    ACTIVE_STATUSES,
    CANCELED,
    COMPLETED,
    IN_PROGRESS,
    NO_SHOW,
    RESERVED,
)

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
    report_skipped_at: datetime | None = None   # ⑬ 하루 마무리에서 "알림장을 보내지 않음"으로 넘긴 때
    series_id: int | None = None   # ⑭ 한꺼번에 잡은 반복 예약의 묶음
    # 저장하는 값이 아니다 — 방문을 쓰는 유스케이스가 잠근 뒤 살아 있는 알림장 링크를 읽어 채운다.
    has_live_report: bool = False

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
