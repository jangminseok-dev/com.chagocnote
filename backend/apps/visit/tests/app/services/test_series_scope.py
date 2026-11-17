"""`이후 전부` 의 잠금과 대상 고르기(⑭) — 고객 행 → 방문 행(ID 오름차순, 한 번), 잠근 뒤 다시 읽은 값으로 고른다."""
from dataclasses import replace

import pytest

from visit.app.services.series_scope import lock_scope
from visit.domain.errors import VisitInputError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeVisits, Journal

WEEKLY = (kst(10, 2, 14), kst(10, 9, 14), kst(10, 16, 14))


def _setup(visits_class=FakeVisits):
    journal = Journal()
    visits, directory = visits_class(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102))
    rows = {(at, pet): visits.seed(pet_id=pet, starts_at=at, series_id=7) for at in WEEKLY for pet in (101, 102)}
    return journal, visits, directory, rows


def _locks(journal):
    return [entry for entry in journal if entry[0] in ("lock_family", "lock_visits")]


async def _scope(visits, directory, ids, **change):
    options = dict(following=True, family=True, skip_ids=frozenset()) | change
    return await lock_scope(ctx(), ids, visits=visits, directory=directory, **options)


async def test_이후_전부는_고객_행을_잠근_뒤_대상을_한_번에_ID_순으로_잠근다():
    journal, visits, directory, rows = _setup()
    anchor = rows[(WEEKLY[1], 101)]
    scope = await _scope(visits, directory, [anchor.id])
    expected = [rows[(at, pet)].id for at in WEEKLY[1:] for pet in (101, 102)]
    assert [v.id for v in scope.targets] == expected
    assert [v.id for v in scope.anchors] == [anchor.id]
    assert scope.series_id == 7
    assert _locks(journal) == [("lock_family", 1, ()), ("lock_visits", sorted(expected))]


async def test_묶음이_없는_방문의_following_은_this_와_같다():
    journal, visits, directory, _ = _setup()
    plain = visits.seed(pet_id=101, starts_at=kst(10, 30, 14))
    scope = await _scope(visits, directory, [plain.id])
    assert ([v.id for v in scope.targets], scope.series_id) == ([plain.id], None)
    assert _locks(journal) == [("lock_family", 1, ()), ("lock_visits", [plain.id])]


async def test_this_는_지금의_잠금_그대로다():
    journal, visits, directory, rows = _setup()
    anchor = rows[(WEEKLY[1], 101)]
    scope = await _scope(visits, directory, [anchor.id], following=False)
    assert ([v.id for v in scope.targets], scope.series_id) == ([anchor.id], None)


async def test_회차가_다른_방문을_함께_보내면_VISIT_INPUT():
    _, visits, directory, rows = _setup()
    with pytest.raises(VisitInputError):
        await _scope(visits, directory, [rows[(WEEKLY[0], 101)].id, rows[(WEEKLY[1], 102)].id])


async def test_잠근_뒤_다시_읽은_상태로_고른다():
    class _Racing(FakeVisits):
        """잠그는 순간 다른 요청이 셋째 회차 102 를 미용 중으로 바꿨다."""

        async def lock(self, ctx, visit_ids):
            target = next(v for v in self.rows.values() if (v.starts_at, v.pet_id) == (WEEKLY[2], 102))
            self.rows[target.id] = replace(target, status="in_progress", started_at=WEEKLY[2])
            return await super().lock(ctx, visit_ids)

    _, visits, directory, rows = _setup(_Racing)
    scope = await _scope(visits, directory, [rows[(WEEKLY[1], 101)].id])
    assert rows[(WEEKLY[2], 102)].id not in [v.id for v in scope.targets]
    assert len(scope.targets) == 3


async def test_전부_빼면_바꿀_예약이_없다():
    _, visits, directory, rows = _setup()
    anchor = rows[(WEEKLY[2], 101)]
    with pytest.raises(VisitInputError):
        await _scope(visits, directory, [anchor.id], family=False, skip_ids=frozenset({anchor.id}))
