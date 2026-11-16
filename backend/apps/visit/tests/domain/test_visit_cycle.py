from datetime import date, timedelta

import pytest

from visit.domain.services.visit_cycle import CycleRules, bucket_of, next_start, pet_cycle
from visit.tests.helpers.builders import TZ, kst

TODAY = date(2026, 11, 17)
RULES = CycleRules()


def days_ago(*gaps: int) -> list[date]:
    """오늘부터 거꾸로 — days_ago(0, 42, 84) 는 오늘, 42일 전, 84일 전."""
    return [TODAY - timedelta(days=g) for g in gaps]


def cycle(days: list[date], manual: int | None = None, rules: CycleRules = RULES):
    return pet_cycle(days, manual_weeks=manual, rules=rules, today=TODAY)


def test_완료_방문이_없으면_주기를_모르고_날짜도_없다():
    got = cycle([])
    assert (got.source, got.weeks, got.estimated, got.interval_count) == ("none", 4, True, 0)
    assert (got.last_visit_date, got.due_date, got.last_interval_weeks) == (None, None, None)


def test_한_번_왔으면_매장의_기본_간격으로_어림한다():
    got = cycle(days_ago(10))
    assert (got.source, got.weeks, got.estimated) == ("none", 4, True)
    assert got.last_visit_date == TODAY - timedelta(days=10)
    assert got.due_date == got.last_visit_date + timedelta(weeks=4)


def test_간격_하나는_주기가_아니다_날짜에는_기본_간격_글에는_지난_간격():
    got = cycle(days_ago(0, 14))   # 2주 간격으로 두 번
    assert (got.source, got.interval_count, got.last_interval_weeks) == ("single", 1, 2)
    assert (got.weeks, got.estimated) == (4, True)
    assert got.due_date == TODAY + timedelta(weeks=4)


def test_간격이_둘_이상이면_중앙값을_주로_반올림한다():
    got = cycle(days_ago(0, 42, 84, 140))   # 간격 42·42·56 → 중앙값 42 → 6주
    assert (got.source, got.weeks, got.interval_count, got.estimated) == ("computed", 6, 3, False)
    assert got.last_interval_weeks == 6
    assert got.due_date == TODAY + timedelta(weeks=6)


def test_한_번_늦게_온_것에_흔들리지_않는다():
    # 4주마다 오다가 한 번 10주 만에 왔다 — 중앙값은 4주.
    assert cycle(days_ago(0, 70, 98, 126, 154)).weeks == 4


def test_짝수_개면_가운데_둘의_평균이고_반올림은_반을_올린다():
    # 간격 14·21 → 평균 17.5일 = 2.5주 → 3주.
    assert cycle(days_ago(0, 14, 35)).weeks == 3
    # 간격 14·14·21·21 → 가운데 14·21 → 17.5일 → 3주.
    assert cycle(days_ago(0, 14, 28, 49, 70)).weeks == 3


def test_7일_미만의_간격은_손질로_보고_버린다():
    # 42일 간격 둘 사이에 3일 만의 손질 방문 — 버리면 42·39 → 중앙값 40.5일 → 6주.
    got = cycle(days_ago(0, 3, 42, 84))
    assert (got.source, got.interval_count, got.weeks) == ("computed", 2, 6)
    # 버리고 하나만 남으면 single.
    assert cycle(days_ago(0, 3, 42)).source == "single"


def test_버릴_날_수가_0이면_모든_간격을_센다():
    rules = CycleRules(min_gap_days=0)
    got = cycle(days_ago(0, 3, 42), rules=rules)
    assert (got.source, got.interval_count) == ("computed", 2)


def test_최근_몇_번만_본다():
    # 오래전엔 12주마다, 최근 세 번은 4주마다.
    days = days_ago(0, 28, 56, 84, 168, 252, 336, 420)
    assert cycle(days).weeks == 4                                       # 최근 6번 — 간격 28×3·84×2 → 28일
    assert cycle(days, rules=CycleRules(sample_visits=12)).weeks == 12  # 모두 — 간격 28×3·84×4 → 84일
    assert cycle(days, rules=CycleRules(sample_visits=3)).interval_count == 2


def test_2년보다_오래된_방문은_보지_않는다():
    got = cycle(days_ago(0, 800, 900))
    assert got.source == "none"
    assert got.last_visit_date == TODAY   # 마지막 방문은 그대로다


def test_주기는_1주에서_52주로_자른다():
    assert cycle(days_ago(0, 8, 16)).weeks == 1
    # 2년 창 안에서 가장 긴 주기 — 간격 365일 둘 → 52.1주 → 52주.
    assert cycle(days_ago(0, 365, 730)).weeks == 52


def test_직접_정한_값이_앞선다_어림이_아니다():
    got = cycle(days_ago(0, 14), manual=6)
    assert (got.source, got.weeks, got.estimated) == ("manual", 6, False)
    assert got.due_date == TODAY + timedelta(weeks=6)
    assert got.last_interval_weeks == 2   # 지난 간격은 그대로 알려 준다


def test_매장의_기본_간격을_바꾸면_어림이_따라간다():
    got = cycle(days_ago(5), rules=CycleRules(default_weeks=8))
    assert (got.weeks, got.due_date) == (8, TODAY - timedelta(days=5) + timedelta(weeks=8))


@pytest.mark.parametrize(("due_in", "expected"), [
    (-30, "due"), (-1, "due"), (0, "soon"), (7, "soon"), (8, None), (40, None),
])
def test_곧과_지남의_경계(due_in, expected):
    # 6주 주기로 계산된 아이 — 다음 올 때가 오늘부터 due_in 일 뒤.
    last = TODAY + timedelta(days=due_in) - timedelta(weeks=6)
    days = [last, last - timedelta(weeks=6), last - timedelta(weeks=12)]
    assert bucket_of(cycle(days), TODAY, soon_days=7) == expected


def test_어림인_아이는_곧에_넣지_않고_지남에는_넣는다():
    single = cycle(days_ago(25, 39))       # 간격 하나 — 어림 4주, 다음 올 때 3일 뒤
    assert bucket_of(single, TODAY, soon_days=7) is None
    late = cycle(days_ago(30))             # 한 번 — 어림 4주, 다음 올 때 2일 전
    assert bucket_of(late, TODAY, soon_days=7) == "due"


def test_2주_간격으로_두_번_온_아이는_15일째에_지남이_아니다():
    got = cycle(days_ago(15, 29))
    assert bucket_of(got, TODAY, soon_days=7) is None


def test_완료_방문이_없는_아이는_묶음이_없다():
    assert bucket_of(cycle([], manual=4), TODAY, soon_days=7) is None


def test_다음_시작은_같은_요일_같은_벽시계_시각이다():
    assert next_start(kst(9, 23, 14), 4, TZ) == kst(10, 21, 14)
