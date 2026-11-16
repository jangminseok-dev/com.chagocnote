"""보내는 시각의 규칙 — 전날 리마인드, 다음 예약 제안, 야간 미룸, 너무 늦음, 재시도, 설정 범위(설계 2·5.2~5.4).

전부 순수 함수다. 시각은 UTC 로 받고 주며, "전날"·"08:00~21:00" 같은 날짜·벽시계 판단만 매장 시간대로 한다.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.errors import NotificationInputError

DAY_START, DAY_END = time(8, 0), time(21, 0)                  # 리마인드·다음 예약 제안을 보내는 시간
REMINDER_TIME_MIN, REMINDER_TIME_MAX = time(8, 0), time(21, 0)
NEXT_VISIT_WEEKS_MIN, NEXT_VISIT_WEEKS_MAX = 1, 52
COOLDOWN_DAYS_MIN, COOLDOWN_DAYS_MAX = 1, 365
MAX_ATTEMPTS = 3
STUCK_CODE = "STUCK"           # 회수 상한에 닿은 sending 줄의 error_code
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))   # 실패 0·1·2회 뒤
STUCK_AFTER = timedelta(minutes=5)          # 이보다 오래 sending 이면 다음 루프가 되돌린다
ACCEPTED_TIMEOUT = timedelta(hours=24)      # accepted 의 최종 상태를 기다리는 최대 시간
TOO_LATE_MARGIN = timedelta(hours=1)        # 예약 이 시간 전을 넘기면 보내지 않는다
MOBILE_NUMBER = re.compile(r"010[0-9]{8}")


def _local_date(at: datetime, tz: str) -> date:
    return at.astimezone(ZoneInfo(tz)).date()


def _at(day: date, wall_time: time, tz: str) -> datetime:
    """매장 시간대의 날짜 + 벽시계 시각을 UTC 로."""
    return datetime.combine(day, wall_time, tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


def reminder_at(starts_at: datetime, reminder_time: time, tz: str, now: datetime) -> datetime | None:
    """예약 전날(매장 시간대 날짜 - 1일) reminder_time. 그 시각이 now 이하이면 None — 접수 문안이 겸한다."""
    at = _at(_local_date(starts_at, tz) - timedelta(days=1), reminder_time, tz)
    return at if at > now else None


def next_visit_weeks(
    cycle_weeks: int | None, cycle_source: str, default_cycle_weeks: int, fixed_weeks: int | None,
) -> int:
    """다음 예약 제안의 주 수(⑬ 설계 3.4) — 아이에게 직접 정한 값 → 매장 알림 설정의 고정 주 수 → 지난 방문에서
    계산한 값(간격 둘 이상) → 매장의 기본 간격. 간격 하나(single)는 주기가 아니라 쓰지 않는다.
    아이를 보고 정한 값이 "모든 아이에게 같은 주 수"보다 구체적이라 앞선다."""
    if cycle_source == "manual" and cycle_weeks is not None:
        return cycle_weeks
    if fixed_weeks is not None:
        return fixed_weeks
    if cycle_source == "computed" and cycle_weeks is not None:
        return cycle_weeks
    return default_cycle_weeks


def next_visit_at(completed_at: datetime, weeks: int, reminder_time: time, tz: str) -> datetime:
    """완료일 + weeks 주 되는 날 reminder_time."""
    return _at(_local_date(completed_at, tz) + timedelta(weeks=weeks), reminder_time, tz)


def deferred_for_daytime(at: datetime, tz: str) -> datetime:
    """매장 시간대로 DAY_START~DAY_END 안이면 그대로. 그 전이면 같은 날 DAY_START, 그 뒤면 다음 날 DAY_START."""
    local = at.astimezone(ZoneInfo(tz))
    if local.time() < DAY_START:
        return _at(local.date(), DAY_START, tz)
    if local.time() > DAY_END:
        return _at(local.date() + timedelta(days=1), DAY_START, tz)
    return at


def is_too_late(send_at: datetime, starts_at: datetime) -> bool:
    return send_at > starts_at - TOO_LATE_MARGIN


def retry_at(attempts: int, now: datetime) -> datetime | None:
    """attempts 는 지금까지 실패한 횟수(이번 실패를 세기 전). 0·1·2 면 1분·5분·30분 뒤, MAX_ATTEMPTS 이상이면 None."""
    if attempts >= MAX_ATTEMPTS:
        return None
    return now + RETRY_DELAYS[attempts]


def check_settings(settings: NotificationSettings) -> None:
    if not REMINDER_TIME_MIN <= settings.reminder_time <= REMINDER_TIME_MAX:
        raise NotificationInputError("리마인드 시각은 08:00 부터 21:00 사이여야 합니다.")
    weeks = settings.next_visit_after_weeks
    if weeks is not None and not NEXT_VISIT_WEEKS_MIN <= weeks <= NEXT_VISIT_WEEKS_MAX:
        raise NotificationInputError("다음 예약 제안 주기는 1주부터 52주 사이여야 합니다.")
    if not COOLDOWN_DAYS_MIN <= settings.next_visit_cooldown_days <= COOLDOWN_DAYS_MAX:
        raise NotificationInputError("다음 예약 제안 간격은 1일부터 365일 사이여야 합니다.")


def is_mobile_number(phone: str) -> bool:
    """010 으로 시작하는 숫자 11자리(customers.phone 저장 형식)."""
    return MOBILE_NUMBER.fullmatch(phone) is not None
