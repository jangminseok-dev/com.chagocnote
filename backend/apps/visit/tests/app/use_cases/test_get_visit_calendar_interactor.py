from datetime import date, time

import pytest

from visit.app.dtos.get_visit_calendar_dto import GetVisitCalendarQuery
from visit.app.use_cases.get_visit_calendar_interactor import GetVisitCalendarInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeLibrary, FakeRecords, FakeSchedule, FakeVisits

NOW = kst(9, 23, 15)


def _setup():
    visits = FakeVisits()
    schedule = FakeSchedule(settings=ScheduleSettings(time(10), time(19), 120, frozenset({0})))
    return visits, schedule, GetVisitCalendarInteractor(visits, schedule, FakeRecords(visits), FakeLibrary(),
                                                        now=lambda: NOW)


async def test_날마다_마릿수_완료_예약_정리_안_됨_휴무():
    visits, schedule, interactor = _setup()
    visits.seed(pet_id=101, starts_at=kst(9, 2, 10), status="completed", started_at=kst(9, 2, 10),
                completed_at=kst(9, 2, 11))
    visits.seed(pet_id=102, starts_at=kst(9, 2, 10))                                   # 정리 안 됨
    visits.seed(pet_id=103, starts_at=kst(9, 2, 12), status="no_show")                 # 마릿수에 안 든다
    visits.seed(pet_id=104, starts_at=kst(9, 25, 14))
    visits.seed(pet_id=105, starts_at=kst(10, 1, 0, 10))                                # 다음 달
    visits.seed(pet_id=106, starts_at=kst(8, 31, 23, 50), duration_minutes=10)          # 지난달 마지막 날
    schedule.closed[(1, date(2026, 9, 17))] = ClosedDate(day=date(2026, 9, 17), note=None)
    view = await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=2026, month=9))
    assert len(view.days) == 30
    second, seventeenth, twenty_fifth = view.days[1], view.days[16], view.days[24]
    assert (second.visit_count, second.completed_count, second.open_count, second.unresolved_count) == (2, 1, 1, 1)
    assert (twenty_fifth.visit_count, twenty_fifth.open_count, twenty_fifth.unresolved_count) == (1, 1, 0)
    assert seventeenth.closed_day and view.days[6].closed_day   # 임시 휴무, 월요일(9/7)
    assert sum(d.visit_count for d in view.days) == 3


async def test_정리_안_된_예약은_달과_상관없이_매장_전체를_센다():
    visits, _, interactor = _setup()
    visits.seed(pet_id=101, starts_at=kst(7, 14, 10))
    visits.seed(pet_id=102, starts_at=kst(9, 22, 10))
    visits.seed(pet_id=103, starts_at=kst(9, 23, 10))   # 오늘 — 아직 정리할 때가 아니다
    visits.seed(pet_id=104, starts_at=kst(7, 1, 10), shop_id=2)
    view = await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=2026, month=10))
    assert (view.unresolved_total, view.oldest_unresolved_date) == (2, date(2026, 7, 14))


async def test_정리할_것이_없으면_가장_이른_날도_없다():
    _, _, interactor = _setup()
    view = await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=2026, month=9))
    assert (view.unresolved_total, view.oldest_unresolved_date) == (0, None)


@pytest.mark.parametrize(("year", "month"), [(2026, 13), (1999, 1)])
async def test_달이_이상하면_VALIDATION_ERROR_다(year, month):
    _, _, interactor = _setup()
    with pytest.raises(VisitInputError):
        await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=year, month=month))


async def test_완료_방문의_대표_사진을_시작_순으로_최대_네_장():
    visits = FakeVisits()
    records, library = FakeRecords(visits), FakeLibrary()
    interactor = GetVisitCalendarInteractor(visits, FakeSchedule(), records, library, now=lambda: NOW)
    done = dict(status="completed", started_at=kst(9, 2, 9), completed_at=kst(9, 2, 18))
    for hour, pet in ((15, 105), (10, 101), (11, 102), (12, 103), (13, 104)):
        v = visits.seed(pet_id=pet, starts_at=kst(9, 2, hour), **done)
        library.add(pet, attached=True)
        records.seed(record(v.id, media=((pet, "photo", "after", 0),)))
    working = visits.seed(pet_id=106, starts_at=kst(9, 2, 9), status="in_progress", started_at=kst(9, 2, 9))
    library.add(106, attached=True)
    records.seed(record(working.id, media=((106, "photo", "after", 0),)))   # 미용 중은 달력에 없다
    view = await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=2026, month=9))
    second = view.days[1]
    assert (second.cover, second.covers) == ("t/101", ["t/101", "t/102", "t/103", "t/104"])
    assert (view.days[2].cover, view.days[2].covers) == (None, [])
