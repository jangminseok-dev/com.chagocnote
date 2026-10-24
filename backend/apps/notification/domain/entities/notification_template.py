from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NotificationTemplate:
    """매장 채널에 등록한 종류별 템플릿 한 줄(설계 4.3). 문안은 코드에 있고(text_version) 여기엔 심사 상태만 있다."""

    id: int
    shop_id: int
    kind: str
    text_version: int
    provider_template_id: str
    status: str
    rejected_reason: str | None
    requested_at: datetime
    decided_at: datetime | None
