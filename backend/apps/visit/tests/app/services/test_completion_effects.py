"""완료 후속 처리 — 완료가 생기거나 풀릴 때만 최근 방문을 다시 계산해 customer 에 넘긴다."""
from dataclasses import replace

from visit.app.services.completion_effects import apply_completion_effects, completion_changed
from visit.tests.helpers.builders import ctx, kst, visit
from visit.tests.helpers.fakes import FakeDirectory, FakeVisits, Journal


def _setup():
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101,))
    return journal, visits, directory


def test_완료가_생기면_바뀐_것이다():
    before = [visit(status="in_progress", started_at=kst(9, 23, 13))]
    after = [replace(before[0], status="completed", completed_at=kst(9, 23, 14))]
    assert completion_changed(before, after)


def test_완료가_풀리면_바뀐_것이다():
    before = [visit(status="completed", started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))]
    after = [replace(before[0], status="reserved", started_at=None, completed_at=None)]
    assert completion_changed(before, after)


def test_완료와_상관없는_전이는_바뀐_것이_아니다():
    before = [visit(status="reserved")]
    after = [replace(before[0], status="canceled", canceled_at=kst(9, 23, 15), cancel_reason="shop_reason")]
    assert not completion_changed(before, after)


async def test_완료가_바뀌면_그_보호자의_마지막_완료_시각을_넘긴다():
    journal, visits, directory = _setup()
    earlier = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                          started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
    today = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13), status="completed",
                        started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))
    reverted = replace(today, status="reserved", started_at=None, completed_at=None)
    visits.rows[today.id] = reverted
    await apply_completion_effects(ctx(), [today], [reverted], visits, directory)
    assert journal == [("set_last_visit", 1, earlier.starts_at)]


async def test_완료가_바뀌지_않으면_아무것도_부르지_않는다():
    journal, visits, directory = _setup()
    reserved = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    started = replace(reserved, status="in_progress", started_at=kst(9, 23, 13))
    await apply_completion_effects(ctx(), [reserved], [started], visits, directory)
    assert journal == []
