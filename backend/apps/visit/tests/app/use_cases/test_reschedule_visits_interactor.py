import pytest

from hub.app.dtos.visit_events import VisitRescheduled
from visit.app.dtos.reschedule_visits_dto import RescheduleVisitsCommand
from visit.app.use_cases.reschedule_visits_interactor import RescheduleVisitsInteractor
from visit.domain.errors import (
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitGroupMismatchError,
    VisitInputError,
    VisitNotFoundError,
    VisitStateConflictError,
)
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeEvents, FakeMenus, FakeSchedule, FakeVisits, Journal

NOW = kst(9, 23, 15)


def _setup():
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102))
    directory.family(2, pets=(201,))
    events = FakeEvents(journal)
    interactor = RescheduleVisitsInteractor(visits, visits, FakeMenus(), FakeSchedule(), directory, events=events,
                                            now=lambda: NOW)
    return journal, visits, interactor, events


def _move(ids, starts_at=kst(10, 3, 15), shop_id=1):
    return RescheduleVisitsCommand(ctx=ctx(shop_id=shop_id), visit_ids=tuple(ids), starts_at=starts_at)


async def test_가족_묶음을_함께_옮긴다():
    journal, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=90)
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14), duration_minutes=120)
    result = await interactor.reschedule_visits(_move([bori.id, kong.id]))
    assert [(v.visit_id, v.starts_at.isoformat()) for v in result.visits] == [
        (kong.id, "2026-10-03T15:00:00+09:00"), (bori.id, "2026-10-03T15:00:00+09:00")]
    assert result.warnings == []
    names = [entry[0] for entry in journal]
    assert names.index("lock_family") < names.index("lock_visits") < names.index("reschedule")


async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다():
    """V14"""
    journal, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    other = visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 14))
    with pytest.raises(VisitGroupMismatchError):
        await interactor.reschedule_visits(_move([kong.id, other.id]))
    assert journal == []


async def test_예약됨이_아닌_방문이_있으면_하나도_옮기지_않는다():
    journal, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 14), status="in_progress",
                       started_at=kst(9, 23, 14))
    with pytest.raises(VisitStateConflictError):
        await interactor.reschedule_visits(_move([kong.id, bori.id]))
    assert "reschedule" not in [entry[0] for entry in journal]
    assert events.published == []


async def test_가장_긴_소요로_자정_넘김을_본다():
    _, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=60)
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14), duration_minutes=180)
    with pytest.raises(VisitCrossesMidnightError):
        await interactor.reschedule_visits(_move([kong.id, bori.id], starts_at=kst(10, 3, 22)))


async def test_없는_방문_범위_밖_시각_중복():
    _, visits, interactor, _ = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 3, 15))
    with pytest.raises(VisitNotFoundError):
        await interactor.reschedule_visits(_move([kong.id, 999]))
    with pytest.raises(VisitInputError):
        await interactor.reschedule_visits(_move([kong.id], starts_at=kst(10, 3, 15, 5)))
    with pytest.raises(VisitDuplicateError):
        await interactor.reschedule_visits(_move([kong.id]))
    theirs = visits.seed(customer_id=9, shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.reschedule_visits(_move([theirs.id]))


async def test_옮긴_방문마다_VisitRescheduled_를_옮긴_뒤에_발행한다():
    journal, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
    await interactor.reschedule_visits(_move([bori.id, kong.id]))
    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.previous_starts_at, e.starts_at, e.occurred_at,
             e.family_pet_ids)
            for e in events.published] == [
        (VisitRescheduled, ctx(), kong.id, 1, 101, kst(10, 2, 14), kst(10, 3, 15), NOW, (101, 102)),
        (VisitRescheduled, ctx(), bori.id, 1, 102, kst(10, 2, 14), kst(10, 3, 15), NOW, (101, 102))]
    names = [entry[0] for entry in journal]
    assert names.index("reschedule") < names.index("publish")


async def test_옮긴_방문마다_다시_색인하라고_알린다():
    """날짜가 바뀌면 검색 문서의 날짜도 바뀐다."""
    _, visits, interactor, events = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
    await interactor.reschedule_visits(_move([kong.id, bori.id]))
    assert events.changed == [("visit", kong.id), ("visit", bori.id)]
