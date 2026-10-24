from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NotificationMessage:
    """알림 줄 하나 — 큐이자 발송 기록(설계 4.4). 전화번호·이름은 저장하지 않고 보내는 순간 포트로 읽는다."""

    id: int
    shop_id: int
    visit_id: int
    customer_id: int
    kind: str
    scheduled_at: datetime            # UTC. 즉시면 만든 시각
    status: str
    attempts: int
    next_attempt_at: datetime | None
    channel_used: str | None          # 실제로 나간 길
    provider_message_id: str | None
    error_code: str | None
    error_kind: str | None            # transient / permanent
    variables: Mapping[str, str]      # 이벤트에서만 알 수 있는 값(url, expires_at ISO, previous_starts_at ISO …)
    requested_by_member_id: int | None
    created_at: datetime
    sent_at: datetime | None
    canceled_reason: str | None
