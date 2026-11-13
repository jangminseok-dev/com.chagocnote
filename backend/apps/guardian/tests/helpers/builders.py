"""guardian 테스트가 함께 쓰는 값 — 시각과 연결 엔티티를 짧게 만든다."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from guardian.domain.entities.guardian_link import GuardianLink

TZ = "Asia/Seoul"


def kst(month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """2026년 한국 시각을 UTC 로."""
    return datetime(2026, month, day, hour, minute, tzinfo=ZoneInfo(TZ)).astimezone(timezone.utc)


def link(**overrides) -> GuardianLink:
    fields = dict(id=1, user_id=5, shop_id=3, customer_id=7, verified_by="report_link", created_at=kst(11, 13, 10),
                  ended_at=None, ended_by=None)
    fields.update(overrides)
    return GuardianLink(**fields)
