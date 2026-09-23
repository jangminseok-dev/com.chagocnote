from datetime import timedelta

from visit.domain.services.visit_cycle import interval_weeks, next_start
from visit.tests.helpers.builders import TZ, kst


def test_완료_방문이_두_번이_안_되면_4주():
    assert interval_weeks([]) == 4
    assert interval_weeks([kst(9, 2, 14)]) == 4


def test_가장_최근_두_번의_간격을_주_단위로_반올림한다():
    starts = [kst(7, 1, 14), kst(8, 5, 14), kst(9, 2, 14)]   # 마지막 간격 4주
    assert interval_weeks(starts) == 4
    assert interval_weeks([kst(9, 2, 14), kst(8, 16, 14)]) == 2   # 17일 → 2.4주 → 2주
    assert interval_weeks([kst(9, 3, 14), kst(8, 16, 14)]) == 3   # 18일 → 2.6주 → 3주


def test_주기는_1주에서_12주로_자른다():
    assert interval_weeks([kst(9, 2, 10), kst(9, 2, 9)]) == 1
    assert interval_weeks([kst(9, 2, 10), kst(9, 2, 10) - timedelta(weeks=30)]) == 12


def test_다음_시작은_같은_요일_같은_벽시계_시각이다():
    assert next_start(kst(9, 23, 14), 4, TZ) == kst(10, 21, 14)
