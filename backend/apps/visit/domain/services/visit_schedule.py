"""일정 판정 — 끝 시각, 예약 가능 범위, 자정 넘김, 하루의 경계, 겹침·휴무·영업시간 경고.

모든 시각은 시간대가 붙은 datetime 이다. "하루"와 "오늘"은 매장 시간대(ShopContext.timezone)로 센다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from visit.domain.errors import VisitCrossesMidnightError, VisitInputError
from visit.domain.value_objects.schedule_settings import ScheduleSettings

STEP_MINUTES = 10
MIN_DURATION = 10
MAX_DURATION = 600
BOOKING_HORIZON_DAYS = 366   # 오늘 기준 앞뒤 1년

OVERLAP = "overlap"
CLOSED_DAY = "closed_day"
OUTSIDE_HOURS = "outside_hours"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_date(moment: datetime, tz: str) -> date:
    return moment.astimezone(ZoneInfo(tz)).date()


def day_bounds(day: date, tz: str) -> tuple[datetime, datetime]:
    """매장 시간대의 그날 0시와 다음 날 0시(UTC)."""
    zone = ZoneInfo(tz)
    start = datetime.combine(day, time(0), zone)
    end = datetime.combine(day + timedelta(days=1), time(0), zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def at_local(day: date, clock: time, tz: str) -> datetime:
    return datetime.combine(day, clock, ZoneInfo(tz)).astimezone(timezone.utc)


def floor_to_step(moment: datetime, tz: str) -> datetime:
    """10분 단위로 내린다(지금 시작한 손님의 예약 시각). 매장 시간대의 벽시계로 내린다."""
    local = moment.astimezone(ZoneInfo(tz))
    floored = local.replace(minute=local.minute - local.minute % STEP_MINUTES, second=0, microsecond=0)
    return floored.astimezone(timezone.utc)


def check_duration(minutes: int) -> None:
    if not (MIN_DURATION <= minutes <= MAX_DURATION) or minutes % STEP_MINUTES:
        raise VisitInputError("소요 시간은 10분 단위로 10분에서 600분 사이여야 합니다.")


def check_settings(settings: ScheduleSettings) -> None:
    """영업시간은 10분 단위이고 여는 시각이 닫는 시각보다 앞선다. 기본 소요도 소요 규칙을 따른다."""
    for clock in (settings.opens_at, settings.closes_at):
        if clock.minute % STEP_MINUTES or clock.second or clock.microsecond:
            raise VisitInputError("영업시간은 10분 단위여야 합니다.")
    if settings.opens_at >= settings.closes_at:
        raise VisitInputError("여는 시각은 닫는 시각보다 앞서야 합니다.")
    check_duration(settings.default_duration_minutes)


def check_start(starts_at: datetime, now: datetime, tz: str) -> None:
    """예약 시각 — 10분 단위, 오늘 기준 앞뒤 1년 안.

    범위를 한참 벗어난 시각(연도 9999 등)은 매장 시간대로 옮기면 OverflowError 가 나므로,
    aware datetime 끼리의 뺄셈(넘치지 않는다)으로 먼저 걸러 500 대신 422 를 낸다.
    """
    if abs(starts_at - now) > timedelta(days=BOOKING_HORIZON_DAYS + 1):
        raise VisitInputError("예약은 오늘 기준 앞뒤 1년 안에서만 잡을 수 있습니다.")
    local = starts_at.astimezone(ZoneInfo(tz))
    if local.minute % STEP_MINUTES or local.second or local.microsecond:
        raise VisitInputError("예약 시각은 10분 단위여야 합니다.")
    days = (local.date() - local_date(now, tz)).days
    if abs(days) > BOOKING_HORIZON_DAYS:
        raise VisitInputError("예약은 오늘 기준 앞뒤 1년 안에서만 잡을 수 있습니다.")


def check_same_day(starts_at: datetime, duration_minutes: int, tz: str) -> None:
    """끝나는 시각이 그날(매장 시간대) 24시를 넘으면 안 된다. 딱 24시는 된다."""
    _, next_midnight = day_bounds(local_date(starts_at, tz), tz)
    if starts_at + timedelta(minutes=duration_minutes) > next_midnight:
        raise VisitCrossesMidnightError("끝나는 시각이 자정을 넘습니다.")


@dataclass(frozen=True)
class Occupied:
    """시간을 차지한 살아 있는 방문 하나(경고 계산용)."""

    starts_at: datetime
    ends_at: datetime
    group: tuple[int, datetime]   # 가족 묶음 — 같은 묶음끼리는 겹침으로 치지 않는다


def is_closed_day(day: date, settings: ScheduleSettings, closed_dates: frozenset[date]) -> bool:
    return day.weekday() in settings.closed_weekdays or day in closed_dates


def warnings_for(
    starts_at: datetime, duration_minutes: int, group: tuple[int, datetime] | None, tz: str,
    settings: ScheduleSettings, closed_dates: frozenset[date], occupied: list[Occupied],
) -> list[str]:
    """막지 않는 경고. group 이 None 이면 누구의 예약도 아닌 빈 칸을 묻는 것이다(시간 칸)."""
    ends_at = starts_at + timedelta(minutes=duration_minutes)
    found = []
    if any(o.starts_at < ends_at and starts_at < o.ends_at and o.group != group for o in occupied):
        found.append(OVERLAP)
    day = local_date(starts_at, tz)
    if is_closed_day(day, settings, closed_dates):
        found.append(CLOSED_DAY)
    if starts_at < at_local(day, settings.opens_at, tz) or ends_at > at_local(day, settings.closes_at, tz):
        found.append(OUTSIDE_HOURS)
    return found


def hourly_starts(day: date, settings: ScheduleSettings, tz: str) -> list[datetime]:
    """시간 칸 — 영업 시작 시각이 속한 정시부터 닫는 시각 전까지 한 시간마다."""
    first = settings.opens_at.hour
    last = settings.closes_at.hour if settings.closes_at.minute == 0 else settings.closes_at.hour + 1
    return [at_local(day, time(hour), tz) for hour in range(first, last)]
