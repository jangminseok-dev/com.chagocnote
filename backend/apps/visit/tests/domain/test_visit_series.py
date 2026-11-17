"""반복 예약의 회차·이후 전부·걸린 회차·자리 계산(⑭ 설계 3.7) — 순수 함수."""
from datetime import timedelta

from visit.domain.entities.visit import CANCELED, COMPLETED, IN_PROGRESS, RESERVED
from visit.domain.services.visit_cycle import PetCycle
from visit.domain.services.visit_series import (
    CYCLE,
    OUT_OF_RANGE,
    SHOP,
    TAKEN,
    RepeatInterval,
    SeriesConflict,
    SeriesPosition,
    clip_interval,
    conflicts_of,
    earliest_ids,
    following_of,
    move_order,
    plan_occurrences,
    repeat_interval,
    series_position,
    wall_delta,
    wall_shift,
    within_horizon,
)
from visit.tests.helpers.builders import TZ, kst, visit

NOW = kst(11, 17, 10)
WEEK = timedelta(weeks=1)


def cycle(weeks: int, source: str) -> PetCycle:
    return PetCycle(weeks=weeks, source=source, interval_count=0, last_interval_weeks=None, last_visit_date=None,
                    due_date=None, estimated=source in ("single", "none"))


def test_회차는_같은_요일_같은_시각이고_1년을_넘는_회차는_빠진다():
    kept, beyond = plan_occurrences(kst(11, 20, 14), 4, 6, TZ, NOW)
    assert [o.index for o in kept] == [1, 2, 3, 4, 5, 6]
    assert kept[0].starts_at == kst(11, 20, 14)
    assert kept[1].starts_at == kst(12, 18, 14)
    assert beyond == 0

    kept, beyond = plan_occurrences(kst(11, 20, 14), 12, 6, TZ, NOW)   # 12주 × 5 = 60주 뒤는 범위 밖
    assert [o.index for o in kept] == [1, 2, 3, 4, 5]
    assert beyond == 1


def test_범위는_예약_범위와_같다():
    assert within_horizon(NOW + timedelta(days=366), NOW, TZ)
    assert not within_horizon(NOW + timedelta(days=367), NOW, TZ)
    assert within_horizon(NOW - timedelta(days=30), NOW, TZ)   # 지난 날도 1년 안이면 범위 안(지금 등록 규칙과 같다)


def test_간격은_1에서_12로_자른다():
    assert [clip_interval(w) for w in (0, 1, 7, 12, 13, 52)] == [1, 1, 7, 12, 12, 12]


def test_간격_기본값은_아는_주기의_짧은_쪽을_1에서_12로_자르고_모르면_매장_값():
    cycles = {101: cycle(16, "computed"), 102: cycle(20, "manual")}
    assert repeat_interval(cycles, 4) == RepeatInterval(12, CYCLE, 101, 16)
    assert repeat_interval({101: cycle(4, "none")}, 30) == RepeatInterval(12, SHOP, None, None)
    assert repeat_interval({}, 30) == RepeatInterval(12, SHOP, None, None)
    assert repeat_interval({101: cycle(5, "manual"), 102: cycle(5, "computed")}, 4) == RepeatInterval(5, CYCLE, 101, 5)


def test_가족_가운데_짧은_쪽이_어림이면_매장_값을_쓴다():
    # ⑬ 의 가족 규칙(짧은 쪽 — 기본 간격 포함)과 같다. 어림은 그 아이의 주기가 아니라 매장 값이다.
    cycles = {101: cycle(8, "computed"), 102: cycle(4, "single")}
    assert repeat_interval(cycles, 4) == RepeatInterval(4, SHOP, None, None)


def test_벽시계_차이만큼_민다():
    delta = wall_delta(kst(11, 27, 14), kst(11, 28, 15), TZ)
    assert delta == timedelta(days=1, hours=1)
    assert wall_shift(kst(12, 4, 14), delta, TZ) == kst(12, 5, 15)


def _series():
    """가족 101·102 의 4회 묶음. 1회차는 앞선 것, 2회차 102 는 완료, 3회차 101 은 미용 중."""
    rows = []
    vid = 1
    for n, at in enumerate((kst(11, 20, 14), kst(11, 27, 14), kst(12, 4, 14), kst(12, 11, 14)), start=1):
        for pet in (101, 102):
            status = RESERVED
            if (n, pet) == (2, 102):
                status = COMPLETED
            if (n, pet) == (3, 101):
                status = IN_PROGRESS
            rows.append(visit(id=vid, pet_id=pet, starts_at=at, status=status, series_id=7))
            vid += 1
    return rows


def test_이후_전부는_같은_시각_이상의_예약됨만이고_가족을_고를_수_있다():
    rows = _series()
    by = {(r.starts_at, r.pet_id): r for r in rows}
    anchor = by[(kst(11, 27, 14), 101)]
    picked = following_of(rows, [anchor], family=True)
    assert [(r.starts_at, r.pet_id) for r in picked] == [
        (kst(11, 27, 14), 101), (kst(12, 4, 14), 102), (kst(12, 11, 14), 101), (kst(12, 11, 14), 102)]
    alone = following_of(rows, [anchor], family=False)
    assert [(r.starts_at, r.pet_id) for r in alone] == [(kst(11, 27, 14), 101), (kst(12, 11, 14), 101)]
    skipped = following_of(rows, [anchor], family=False, skip_ids=frozenset({by[(kst(12, 11, 14), 101)].id}))
    assert [r.id for r in skipped] == [anchor.id]


def test_가장_가까운_회차의_방문들():
    rows = [visit(id=1, starts_at=kst(12, 4, 14)), visit(id=2, pet_id=102, starts_at=kst(12, 4, 14)),
            visit(id=3, starts_at=kst(12, 11, 14))]
    assert earliest_ids(rows) == frozenset({1, 2})
    assert earliest_ids([]) == frozenset()


def test_늦게_미는_묶음은_늦은_회차부터_당기는_묶음은_이른_회차부터_옮긴다():
    a, b, c = (visit(id=i, starts_at=at) for i, at in ((1, kst(11, 20, 14)), (2, kst(11, 27, 14)), (3, kst(12, 4, 14))))
    later = [(a, a.starts_at + WEEK), (b, b.starts_at + WEEK), (c, c.starts_at + WEEK)]
    assert [v.id for v, _ in move_order(later)] == [3, 2, 1]
    earlier = [(c, c.starts_at - WEEK), (a, a.starts_at - WEEK), (b, b.starts_at - WEEK)]
    assert [v.id for v, _ in move_order(earlier)] == [1, 2, 3]


def test_걸린_회차는_같은_아이의_살아_있는_예약과_1년_범위_밖이다():
    a = visit(id=1, starts_at=kst(11, 27, 14))
    b = visit(id=2, starts_at=kst(12, 4, 14))
    moves = [(a, kst(12, 4, 14)), (b, kst(12, 11, 14))]
    # b 의 옛 자리는 옮기는 대상이라 occupied 에 없다 — 걸리지 않는다
    assert conflicts_of(moves, [], NOW, TZ) == []
    outside = visit(id=9, starts_at=kst(12, 11, 14))                 # 묶음 밖의 같은 아이 예약
    sibling = visit(id=10, pet_id=102, starts_at=kst(12, 4, 14))     # 형제 아이 — 같은 시각이어도 가족 묶음일 뿐
    assert conflicts_of(moves, [outside, sibling], NOW, TZ) == [
        SeriesConflict(visit_id=2, pet_id=101, starts_at=kst(12, 11, 14), reason=TAKEN)]
    far = [(a, NOW + timedelta(days=380))]
    assert [c.reason for c in conflicts_of(far, [], NOW, TZ)] == [OUT_OF_RANGE]


def test_보호자만의_방문은_같은_보호자의_아이_없는_예약과_걸린다():
    a = visit(id=1, pet_id=None, starts_at=kst(11, 27, 14))
    other_family_pet = visit(id=8, pet_id=101, starts_at=kst(12, 4, 14))
    owner_only = visit(id=9, pet_id=None, starts_at=kst(12, 4, 14))
    assert conflicts_of([(a, kst(12, 4, 14))], [other_family_pet], NOW, TZ) == []
    assert [c.visit_id for c in conflicts_of([(a, kst(12, 4, 14))], [owner_only], NOW, TZ)] == [1]


def test_자리는_취소를_빼고_가족은_한_번_세며_취소된_방문은_자기를_넣는다():
    starts = [kst(11, 20, 14) + WEEK * i for i in range(6)]
    rows = [visit(id=i + 1, starts_at=at, status=CANCELED if i == 4 else RESERVED, series_id=7)
            for i, at in enumerate(starts)]
    rows.append(visit(id=20, pet_id=102, starts_at=starts[3], series_id=7))   # 4회차의 형제
    assert series_position(rows, rows[3]) == SeriesPosition(4, 5, False)
    assert series_position(rows, rows[5]) == SeriesPosition(5, 5, True)
    assert series_position(rows, rows[4]) == SeriesPosition(5, 6, False)
