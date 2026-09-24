"""읽기 서명 URL 의 시간 창(설계 7.3).

같은 객체는 하루 동안 같은 URL 이어야 앱 캐시와 ⑤의 CDN 캐시가 맞는다. 서명 시각을 매장 시간대의 가장 최근
04:00 으로 내리고 유효 기간을 48시간으로 두면, 하루 안에서는 서명이 글자까지 같고 남은 유효 시간은 언제나
24~48시간이다. 유출된 URL 이 살아 있는 시간은 최대 48시간이다(위협 M10).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

DAY_STARTS_AT = time(4)
VALID_FOR = timedelta(hours=48)


@dataclass(frozen=True)
class SigningWindow:
    signed_at: datetime   # UTC
    expires_in_seconds: int

    @property
    def expires_at(self) -> datetime:
        return self.signed_at + timedelta(seconds=self.expires_in_seconds)


def signing_window(now: datetime, tz: str) -> SigningWindow:
    local = now.astimezone(ZoneInfo(tz))
    boundary = datetime.combine(local.date(), DAY_STARTS_AT, local.tzinfo)
    if local < boundary:
        boundary -= timedelta(days=1)
    return SigningWindow(signed_at=boundary.astimezone(timezone.utc), expires_in_seconds=int(VALID_FOR.total_seconds()))
