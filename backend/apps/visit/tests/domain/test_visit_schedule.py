from datetime import date, datetime, time

import pytest

from visit.domain.errors import VisitCrossesMidnightError, VisitInputError
from visit.domain.services.visit_schedule import (
    CLOSED_DAY,
    OUTSIDE_HOURS,
    OVERLAP,
    Occupied,
    check_duration,
    check_same_day,
    check_start,
    day_bounds,
    floor_to_step,
    hourly_starts,
    local_date,
    warnings_for,
)
from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS, ScheduleSettings
from visit.tests.helpers.builders import TZ, kst

NOW = kst(9, 23, 15)


def test_하루의_경계는_매장_시간대의_0시다():
    start, end = day_bounds(date(2026, 9, 23), TZ)
    assert (start, end) == (kst(9, 23), kst(9, 24))
    assert local_date(kst(9, 24, 0, 10), TZ) == date(2026, 9, 24)


@pytest.mark.parametrize("minutes", [10, 90, 600])
def test_소요는_10분_단위로_10분에서_600분(minutes):
    check_duration(minutes)


@pytest.mark.parametrize("minutes", [0, 5, 95, 610])
def test_범위_밖이거나_10분_단위가_아닌_소요는_거절한다(minutes):
    with pytest.raises(VisitInputError):
        check_duration(minutes)


def test_예약_시각은_10분_단위여야_한다():
    check_start(kst(9, 30, 14, 20), NOW, TZ)
    with pytest.raises(VisitInputError):
        check_start(kst(9, 30, 14, 25), NOW, TZ)


def test_예약은_오늘_기준_앞뒤_1년까지():
    from datetime import timedelta

    check_start(kst(9, 23, 10) + timedelta(days=366), NOW, TZ)
    check_start(kst(9, 23, 10) - timedelta(days=366), NOW, TZ)   # 카톡의 지난 방문을 옮겨 적는다
    with pytest.raises(VisitInputError):
        check_start(kst(9, 23, 10) + timedelta(days=367), NOW, TZ)
    with pytest.raises(VisitInputError):
        check_start(kst(9, 23, 10) - timedelta(days=367), NOW, TZ)


@pytest.mark.parametrize("starts_at", [
    datetime.fromisoformat("9999-12-31T23:50:00+00:00"),
    datetime.fromisoformat("0001-01-01T00:00:00+10:00"),
])
def test_범위를_한참_벗어난_시각은_시간대로_옮기기_전에_거절한다(starts_at):
    """astimezone 이 OverflowError 를 내기 전에 뺄셈으로 먼저 막는다 — 500 대신 422."""
    with pytest.raises(VisitInputError):
        check_start(starts_at, NOW, TZ)


def test_딱_자정에_끝나면_된다():
    check_same_day(kst(9, 23, 22), 120, TZ)


def test_자정을_넘기면_VISIT_CROSSES_MIDNIGHT_다():
    with pytest.raises(VisitCrossesMidnightError):
        check_same_day(kst(9, 23, 22), 130, TZ)


def test_지금_시작한_손님의_예약_시각은_10분_단위로_내린다():
    assert floor_to_step(kst(9, 23, 15, 37), TZ) == kst(9, 23, 15, 30)


def _warn(starts_at, minutes=60, group=(9, kst(1, 1)), settings=DEFAULT_SETTINGS, closed=(), occupied=()):
    return warnings_for(starts_at, minutes, group, TZ, settings, frozenset(closed), list(occupied))


def test_경고가_없는_예약():
    assert _warn(kst(9, 23, 11)) == []


def test_다른_묶음과_시간이_겹치면_overlap():
    other = Occupied(kst(9, 23, 11), kst(9, 23, 12), group=(2, kst(9, 23, 11)))
    assert _warn(kst(9, 23, 11, 30), occupied=[other]) == [OVERLAP]


def test_끝과_시작이_맞닿으면_겹치지_않는다():
    other = Occupied(kst(9, 23, 11), kst(9, 23, 12), group=(2, kst(9, 23, 11)))
    assert _warn(kst(9, 23, 12), occupied=[other]) == []


def test_같은_가족_묶음끼리는_겹침이_아니다():
    """두부·보리를 같은 시각에 맡기면 방문 둘이 같은 시간을 차지하지만 경고할 일이 아니다."""
    group = (1, kst(9, 23, 13))
    sibling = Occupied(kst(9, 23, 13), kst(9, 23, 14), group=group)
    assert _warn(kst(9, 23, 13), group=group, occupied=[sibling]) == []


def test_묶음_없이_물으면_어떤_예약과도_겹친다():
    other = Occupied(kst(9, 23, 13), kst(9, 23, 14), group=(1, kst(9, 23, 13)))
    assert _warn(kst(9, 23, 13), group=None, occupied=[other]) == [OVERLAP]


def test_쉬는_요일과_임시_휴무는_closed_day():
    monday_off = ScheduleSettings(time(10), time(19), 120, frozenset({0}))
    assert _warn(kst(9, 28, 11), settings=monday_off) == [CLOSED_DAY]   # 9/28 은 월요일
    assert _warn(kst(9, 25, 11), closed=[date(2026, 9, 25)]) == [CLOSED_DAY]


def test_영업시간_밖으로_나가면_outside_hours():
    assert _warn(kst(9, 23, 9, 30)) == [OUTSIDE_HOURS]            # 여는 시각 전에 시작
    assert _warn(kst(9, 23, 18, 30)) == [OUTSIDE_HOURS]           # 닫는 시각 뒤에 끝남
    assert _warn(kst(9, 23, 18), minutes=60) == []                # 딱 닫는 시각에 끝남


def test_경고는_여러_개가_함께_나온다():
    other = Occupied(kst(9, 25, 8), kst(9, 25, 10), group=(2, kst(9, 25, 8)))
    assert _warn(kst(9, 25, 9), closed=[date(2026, 9, 25)], occupied=[other]) == [
        OVERLAP, CLOSED_DAY, OUTSIDE_HOURS,
    ]


def test_시간_칸은_영업시간의_정시마다():
    slots = hourly_starts(date(2026, 9, 23), DEFAULT_SETTINGS, TZ)
    assert slots == [kst(9, 23, hour) for hour in range(10, 19)]


def test_영업시간이_정시가_아니면_걸친_정시를_모두_보인다():
    settings = ScheduleSettings(time(9, 30), time(18, 30), 120, frozenset())
    assert hourly_starts(date(2026, 9, 23), settings, TZ) == [kst(9, 23, h) for h in range(9, 19)]
