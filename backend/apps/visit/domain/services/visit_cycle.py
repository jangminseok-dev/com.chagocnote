"""다음 예약 — 그 아이의 방문 주기와, 같은 요일·같은 시각의 다음 시작 시각."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_WEEKS = 4
MIN_WEEKS = 1
MAX_WEEKS = 12


def interval_weeks(completed_starts: list[datetime]) -> int:
    """가장 최근 두 완료 방문의 간격을 주 단위로 반올림한다. 두 번이 안 되면 4주. 1~12주로 자른다."""
    if len(completed_starts) < 2:
        return DEFAULT_WEEKS
    latest, previous = sorted(completed_starts, reverse=True)[:2]
    weeks = round((latest - previous) / timedelta(weeks=1))
    return max(MIN_WEEKS, min(MAX_WEEKS, weeks))


def next_start(source_starts_at: datetime, weeks: int, tz: str) -> datetime:
    """weeks 주 뒤의 같은 요일·같은 벽시계 시각."""
    local = source_starts_at.astimezone(ZoneInfo(tz))
    wall = local.replace(tzinfo=None) + timedelta(weeks=weeks)
    return wall.replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
