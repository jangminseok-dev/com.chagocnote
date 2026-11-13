"""매출을 보는 기간 — 일·주·월·연의 경계, 앞 기간, 진행 중일 때 견줄 창, 막대의 칸(설계 ⑧ 3.1).

날짜는 모두 매장 시간대의 날짜다. 여기서는 시간대를 다루지 않는다 — 오늘이 며칠인지는 부르는 쪽이 준다.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

Span = Literal["day", "week", "month", "year"]

# 받는 anchor 의 범위. 이 밖의 앞 기간(1999년)·끝 주(2101-01-02)도 date 로 계산은 된다.
MIN_ANCHOR, MAX_ANCHOR = date(2000, 1, 1), date(2100, 12, 31)

_DAY = timedelta(days=1)


@dataclass(frozen=True)
class Period:
    """기간 하나. start·end 는 첫날과 끝날(둘 다 품는다)."""

    span: Span
    start: date
    end: date

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    @property
    def until(self) -> date:
        """끝 다음 날 — 반열린 구간의 끝."""
        return self.end + _DAY


def _month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _same_day(year: int, month: int, day: int) -> date:
    """그 해·달의 같은 날짜. 없으면(2월 30일, 평년의 2월 29일) 그 달의 말일."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def period_of(span: Span, anchor: date) -> Period:
    """anchor 가 든 기간. 주는 월요일부터 일요일이다."""
    if span == "day":
        return Period(span, anchor, anchor)
    if span == "week":
        monday = anchor - timedelta(days=anchor.weekday())
        return Period(span, monday, monday + timedelta(days=6))
    if span == "month":
        return Period(span, anchor.replace(day=1), _month_end(anchor.year, anchor.month))
    return Period(span, date(anchor.year, 1, 1), date(anchor.year, 12, 31))


def previous_of(period: Period) -> Period:
    """바로 앞 기간 — 어제·지난주·지난달·작년."""
    return period_of(period.span, period.start - _DAY)


def year_ago_of(period: Period) -> Period | None:
    """한 해 전의 같은 기간. 연 보기에서는 앞 기간이 곧 작년이라 None 이다.

    주는 첫날의 같은 날짜를 한 해 앞으로 옮긴 이레다(요일은 맞추지 않는다 — 같은 때를 견주려는 것이다).
    """
    if period.span == "year":
        return None
    start = _same_day(period.start.year - 1, period.start.month, period.start.day)
    if period.span == "day":
        return Period("day", start, start)
    if period.span == "week":
        return Period("week", start, start + timedelta(days=6))
    return period_of("month", start)


def elapsed_end(period: Period, today: date) -> date | None:
    """기간 가운데 지나간 마지막 날 — 진행 중이면 오늘, 지났으면 끝날, 아직 오지 않았으면 None."""
    if today < period.start:
        return None
    return min(today, period.end)


def compare_window(period: Period, other: Period, today: date) -> tuple[date, date] | None:
    """period 를 other(앞 기간이나 작년)와 견줄 때 other 에서 볼 날들(첫날, 끝날 — 둘 다 품는다).

    지난 기간은 other 전체와, 진행 중인 기간은 같은 길이만큼만 견준다 — 11월 14일에 보는 11월은 10월 1~14일과.
    같은 길이: 일·주는 지난 날 수, 월은 같은 날짜(그 달에 없으면 말일), 연은 같은 월·일(2월 29일은 28일).
    아직 오지 않은 기간은 견주지 않는다(None).
    """
    reached = elapsed_end(period, today)
    if reached is None:
        return None
    if reached == period.end:
        return other.start, other.end
    if period.span == "month":
        end = _same_day(other.start.year, other.start.month, reached.day)
    elif period.span == "year":
        end = _same_day(other.start.year, reached.month, reached.day)
    else:
        end = other.start + (reached - period.start)
    return other.start, min(end, other.end)


def bucket_keys(period: Period) -> list[date]:
    """막대의 칸 — 주·월은 날마다, 연은 달마다(그 달의 1일), 일은 없다."""
    if period.span == "day":
        return []
    if period.span == "year":
        return [date(period.start.year, month, 1) for month in range(1, 13)]
    return [period.start + timedelta(days=i) for i in range((period.end - period.start).days + 1)]
