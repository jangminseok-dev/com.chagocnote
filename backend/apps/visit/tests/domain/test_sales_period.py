from datetime import date

import pytest

from visit.domain.services.sales_period import (
    Period,
    bucket_keys,
    compare_window,
    elapsed_end,
    period_of,
    previous_of,
    year_ago_of,
)


@pytest.mark.parametrize("span,anchor,start,end", [
    ("day", date(2026, 11, 14), date(2026, 11, 14), date(2026, 11, 14)),
    ("week", date(2026, 11, 14), date(2026, 11, 9), date(2026, 11, 15)),     # 토요일 → 월~일
    ("week", date(2026, 11, 9), date(2026, 11, 9), date(2026, 11, 15)),      # 월요일 자신
    ("week", date(2026, 11, 15), date(2026, 11, 9), date(2026, 11, 15)),     # 일요일은 그 주의 끝
    ("week", date(2027, 1, 1), date(2026, 12, 28), date(2027, 1, 3)),        # 해를 걸친 주
    ("week", date(2100, 12, 31), date(2100, 12, 27), date(2101, 1, 2)),      # 받는 범위의 끝
    ("month", date(2028, 2, 10), date(2028, 2, 1), date(2028, 2, 29)),       # 윤년
    ("month", date(2026, 2, 28), date(2026, 2, 1), date(2026, 2, 28)),
    ("month", date(2026, 12, 31), date(2026, 12, 1), date(2026, 12, 31)),
    ("year", date(2026, 6, 1), date(2026, 1, 1), date(2026, 12, 31)),
    ("year", date(2100, 12, 31), date(2100, 1, 1), date(2100, 12, 31)),
])
def test_기간의_첫날과_끝날(span, anchor, start, end):
    period = period_of(span, anchor)
    assert (period.span, period.start, period.end) == (span, start, end)


def test_until_은_끝_다음_날이고_contains_는_양_끝을_품는다():
    november = period_of("month", date(2026, 11, 14))
    assert november.until == date(2026, 12, 1)
    assert november.contains(date(2026, 11, 1)) and november.contains(date(2026, 11, 30))
    assert not november.contains(date(2026, 10, 31)) and not november.contains(date(2026, 12, 1))


@pytest.mark.parametrize("span,anchor,start,end", [
    ("day", date(2026, 11, 14), date(2026, 11, 13), date(2026, 11, 13)),
    ("day", date(2026, 1, 1), date(2025, 12, 31), date(2025, 12, 31)),
    ("week", date(2026, 11, 14), date(2026, 11, 2), date(2026, 11, 8)),
    ("week", date(2027, 1, 1), date(2026, 12, 21), date(2026, 12, 27)),      # 해를 걸친 주의 앞 주
    ("month", date(2026, 3, 31), date(2026, 2, 1), date(2026, 2, 28)),
    ("month", date(2026, 1, 15), date(2025, 12, 1), date(2025, 12, 31)),
    ("year", date(2026, 6, 1), date(2025, 1, 1), date(2025, 12, 31)),
    ("year", date(2000, 1, 1), date(1999, 1, 1), date(1999, 12, 31)),        # 받는 범위 밖도 계산은 된다
])
def test_앞_기간은_어제_지난주_지난달_작년이다(span, anchor, start, end):
    previous = previous_of(period_of(span, anchor))
    assert (previous.span, previous.start, previous.end) == (span, start, end)


@pytest.mark.parametrize("span,anchor,start,end", [
    ("day", date(2026, 11, 14), date(2025, 11, 14), date(2025, 11, 14)),
    ("day", date(2028, 2, 29), date(2027, 2, 28), date(2027, 2, 28)),        # 윤일
    ("week", date(2026, 11, 14), date(2025, 11, 9), date(2025, 11, 15)),     # 같은 날짜를 한 해 앞으로
    ("month", date(2026, 11, 14), date(2025, 11, 1), date(2025, 11, 30)),
    ("month", date(2028, 2, 10), date(2027, 2, 1), date(2027, 2, 28)),
])
def test_작년_같은_기간(span, anchor, start, end):
    ago = year_ago_of(period_of(span, anchor))
    assert ago is not None
    assert (ago.span, ago.start, ago.end) == (span, start, end)


def test_연_보기에는_작년_같은_기간이_따로_없다():
    assert year_ago_of(period_of("year", date(2026, 6, 1))) is None


@pytest.mark.parametrize("today,expected", [
    (date(2026, 11, 14), date(2026, 11, 14)),   # 진행 중
    (date(2026, 11, 1), date(2026, 11, 1)),
    (date(2026, 11, 30), date(2026, 11, 30)),
    (date(2026, 12, 5), date(2026, 11, 30)),    # 지난 기간
    (date(2026, 10, 31), None),                 # 앞날의 기간
])
def test_지나간_끝(today, expected):
    assert elapsed_end(period_of("month", date(2026, 11, 14)), today) == expected


@pytest.mark.parametrize("span,anchor,today,start,end", [
    # 11월 14일에 보는 11월은 10월 1~14일과.
    ("month", date(2026, 11, 14), date(2026, 11, 14), date(2026, 10, 1), date(2026, 10, 14)),
    # 3월 31일·30일·29일에 보는 3월은 2월 전체와(2월에 그 날짜가 없다).
    ("month", date(2026, 3, 31), date(2026, 3, 31), date(2026, 2, 1), date(2026, 2, 28)),
    ("month", date(2026, 3, 30), date(2026, 3, 30), date(2026, 2, 1), date(2026, 2, 28)),
    ("month", date(2028, 3, 30), date(2028, 3, 30), date(2028, 2, 1), date(2028, 2, 29)),
    ("month", date(2026, 3, 1), date(2026, 3, 1), date(2026, 2, 1), date(2026, 2, 1)),
    # 수요일에 보는 이번 주는 지난주 월~수와.
    ("week", date(2026, 11, 11), date(2026, 11, 11), date(2026, 11, 2), date(2026, 11, 4)),
    ("week", date(2026, 11, 9), date(2026, 11, 9), date(2026, 11, 2), date(2026, 11, 2)),
    ("day", date(2026, 11, 14), date(2026, 11, 14), date(2026, 11, 13), date(2026, 11, 13)),
    # 2월 29일에 보는 연은 작년 1월 1일~2월 28일과.
    ("year", date(2028, 2, 29), date(2028, 2, 29), date(2027, 1, 1), date(2027, 2, 28)),
    ("year", date(2026, 11, 14), date(2026, 11, 14), date(2025, 1, 1), date(2025, 11, 14)),
])
def test_진행_중인_기간은_같은_길이만큼만_견준다(span, anchor, today, start, end):
    period = period_of(span, anchor)
    assert compare_window(period, previous_of(period), today) == (start, end)


def test_작년과도_같은_길이만큼만_견준다():
    november = period_of("month", date(2026, 11, 14))
    ago = year_ago_of(november)
    assert compare_window(november, ago, date(2026, 11, 14)) == (date(2025, 11, 1), date(2025, 11, 14))
    week = period_of("week", date(2026, 11, 11))
    assert compare_window(week, year_ago_of(week), date(2026, 11, 11)) == (date(2025, 11, 9), date(2025, 11, 11))


@pytest.mark.parametrize("span,anchor", [
    ("day", date(2026, 10, 3)), ("week", date(2026, 10, 3)), ("month", date(2026, 10, 3)), ("year", date(2025, 5, 5)),
])
def test_지난_기간은_앞_기간_전체와_견준다(span, anchor):
    period = period_of(span, anchor)
    previous = previous_of(period)
    assert compare_window(period, previous, date(2026, 11, 14)) == (previous.start, previous.end)


def test_앞날의_기간은_견주지_않는다():
    december = period_of("month", date(2026, 12, 25))
    assert compare_window(december, previous_of(december), date(2026, 11, 14)) is None


def test_칸은_주_7일_월_그_달의_날수_연_12달이고_일에는_없다():
    assert bucket_keys(period_of("day", date(2026, 11, 14))) == []
    week = bucket_keys(period_of("week", date(2027, 1, 1)))
    assert week == [date(2026, 12, 28), date(2026, 12, 29), date(2026, 12, 30), date(2026, 12, 31),
                    date(2027, 1, 1), date(2027, 1, 2), date(2027, 1, 3)]
    assert len(bucket_keys(period_of("month", date(2028, 2, 10)))) == 29
    assert bucket_keys(period_of("month", date(2026, 11, 14)))[-1] == date(2026, 11, 30)
    year = bucket_keys(period_of("year", date(2026, 6, 1)))
    assert year == [date(2026, m, 1) for m in range(1, 13)]


def test_기간은_값이_같으면_같다():
    assert period_of("month", date(2026, 11, 1)) == Period("month", date(2026, 11, 1), date(2026, 11, 30))
