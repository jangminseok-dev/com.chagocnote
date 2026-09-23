from datetime import date, time

import pytest

from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery
from visit.app.use_cases.list_visit_slots_interactor import ListVisitSlotsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeSchedule, FakeVisits

DAY = date(2026, 10, 2)


def _setup(settings=ScheduleSettings(time(10), time(14), 120, frozenset())):
    visits = FakeVisits()
    return visits, ListVisitSlotsInteractor(visits, FakeSchedule(settings=settings))


def _query(**overrides):
    fields = dict(ctx=ctx(), day=DAY, duration_minutes=60, at=None, exclude=())
    fields.update(overrides)
    return ListVisitSlotsQuery(**fields)


async def test_영업시간의_정시마다_경고를_붙인다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 11), duration_minutes=60)
    view = await interactor.list_visit_slots(_query())
    assert [(s.starts_at.hour, s.warnings) for s in view.slots] == [
        (10, []), (11, ["overlap"]), (12, []), (13, [])]
    assert view.slots[0].starts_at.isoformat() == "2026-10-02T10:00:00+09:00"


async def test_같은_가족의_예약과도_겹친다고_알린다():
    """빈 칸을 묻는 것이라 묶음이 없다 — 시간을 차지한 방문이면 누구든 겹침이다."""
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 12))
    view = await interactor.list_visit_slots(_query())
    assert view.slots[2].warnings == ["overlap"]


async def test_옮길_방문은_빼고_본다():
    visits, interactor = _setup()
    mine = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 11), duration_minutes=60)
    view = await interactor.list_visit_slots(_query(exclude=(mine.id,)))
    assert all(s.warnings == [] for s in view.slots)


async def test_한_시각만_물을_수_있고_소요가_없으면_매장_기본이다():
    _, interactor = _setup()
    view = await interactor.list_visit_slots(_query(at=time(13, 10), duration_minutes=None))
    assert view.duration_minutes == 120
    assert [(s.starts_at.hour, s.starts_at.minute, s.warnings) for s in view.slots] == [
        (13, 10, ["outside_hours"])]


async def test_휴무일이면_모든_칸에_closed_day():
    _, interactor = _setup(ScheduleSettings(time(10), time(12), 120, frozenset({4})))   # 10/2 금요일
    view = await interactor.list_visit_slots(_query())
    assert view.closed_day and all("closed_day" in s.warnings for s in view.slots)


@pytest.mark.parametrize("fields", [dict(at=time(13, 5)), dict(duration_minutes=15)])
async def test_10분_단위가_아니면_VALIDATION_ERROR_다(fields):
    _, interactor = _setup()
    with pytest.raises(VisitInputError):
        await interactor.list_visit_slots(_query(**fields))


@pytest.mark.parametrize("day", [date(1, 1, 1), date(9999, 12, 31)])
async def test_범위_밖_날짜는_VALIDATION_ERROR_다(day):
    _, interactor = _setup()
    with pytest.raises(VisitInputError):
        await interactor.list_visit_slots(_query(day=day))
