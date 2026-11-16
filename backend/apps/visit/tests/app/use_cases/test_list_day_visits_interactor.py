from datetime import date, time, timedelta

import pytest

from visit.app.dtos.list_day_visits_dto import ListDayVisitsQuery
from visit.app.use_cases.list_day_visits_interactor import ListDayVisitsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeRevisitSettingsRepository,
    FakeChecks,
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeSchedule,
    FakeVisits,
)

NOW = kst(9, 23, 15)


def _setup(settings=None):
    visits, directory = FakeVisits(), FakeDirectory()
    directory.family(1, pets=(101, 102))
    directory.family(2, pets=(201,), name=None)   # 익명화한 고객
    schedule = FakeSchedule() if settings is None else FakeSchedule(settings=settings)
    interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, FakeRecords(visits),
                                         FakeLibrary(), FakeReportRepository(visits), now=lambda: NOW, checks=FakeChecks(),
                                         revisit_settings=FakeRevisitSettingsRepository())
    return visits, interactor


async def _day(interactor, day, shop_id=1):
    return await interactor.list_day_visits(ListDayVisitsQuery(ctx=ctx(shop_id=shop_id), day=day))


async def test_그날_시작하는_방문을_시작_순으로_상태별로_센다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 10), status="completed",
                started_at=kst(9, 23, 10), completed_at=kst(9, 23, 12))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13), status="in_progress", started_at=kst(9, 23, 13))
    visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 23, 16), status="canceled", canceled_at=NOW,
                cancel_reason="customer_request")
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 24, 10))       # 다음 날
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 11), shop_id=2)   # 다른 매장
    day = await _day(interactor, date(2026, 9, 23))
    assert [(i.visit.pet.pet_id, i.visit.status) for i in day.items] == [
        (101, "completed"), (102, "in_progress"), (201, "canceled")]
    counts = day.counts
    assert (counts.visit_count, counts.completed, counts.in_progress, counts.canceled, counts.reserved) == (
        2, 1, 1, 1, 0)
    assert day.items[2].visit.customer.name is None   # 익명화한 고객은 이름 없이 틀만


async def test_가족_묶음과_다른_묶음과의_겹침():
    """13시 가족은 14시 다른 가족과 겹친다. 17시 가족은 형제끼리만 같은 시간을 차지해 겹침이 아니다."""
    visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 25, 13), duration_minutes=90)
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 25, 13), duration_minutes=90)
    visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 25, 14), duration_minutes=60)
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 25, 17), duration_minutes=60)
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 25, 17), duration_minutes=60)
    day = await _day(interactor, date(2026, 9, 25))
    keys = [i.group_key for i in day.items]
    assert keys[0] == keys[1] == f"1:{kong.starts_at.isoformat()}" != keys[2]
    assert keys[3] == keys[4] != keys[0]
    assert [i.overlapping for i in day.items] == [True, True, True, False, False]


async def test_지난_날의_예약됨은_정리_안_됨이다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 21, 10))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 21, 10), status="no_show")
    day = await _day(interactor, date(2026, 9, 21))
    assert [i.unresolved for i in day.items] == [True, False]
    assert day.counts.unresolved == 1
    today = await _day(interactor, date(2026, 9, 23))
    assert today.counts.unresolved == 0


async def test_휴무일을_알린다():
    _, interactor = _setup(ScheduleSettings(time(10), time(19), 120, frozenset({0})))
    assert (await _day(interactor, date(2026, 9, 28))).closed_day is True     # 월요일
    assert (await _day(interactor, date(2026, 9, 29))).closed_day is False


async def test_범위_밖_날짜는_설정을_읽기_전에_거절한다():
    visits, directory = FakeVisits(), FakeDirectory()
    schedule = FakeSchedule()
    interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, FakeRecords(visits),
                                         FakeLibrary(), FakeReportRepository(visits), now=lambda: NOW, checks=FakeChecks(),
                                         revisit_settings=FakeRevisitSettingsRepository())
    for day in (date(1, 1, 1), date(9999, 12, 31)):
        with pytest.raises(VisitInputError):
            await interactor.list_day_visits(ListDayVisitsQuery(ctx=ctx(), day=day))
    assert schedule.journal == []


async def test_기록이_있는지와_대표_사진을_준다():
    visits, directory = FakeVisits(), FakeDirectory()
    directory.family(1, pets=(101, 102))
    records, library = FakeRecords(visits), FakeLibrary()
    library.add(51, attached=True)
    interactor = ListDayVisitsInteractor(visits, FakeMenus(), FakeSchedule(), directory, records, library,
                                         FakeReportRepository(visits), now=lambda: NOW, checks=FakeChecks(),
                                         revisit_settings=FakeRevisitSettingsRepository())
    photographed = visits.seed(pet_id=101, starts_at=kst(9, 23, 10), status="in_progress", started_at=kst(9, 23, 10))
    noted = visits.seed(pet_id=102, starts_at=kst(9, 23, 11), status="in_progress", started_at=kst(9, 23, 11))
    visits.seed(pet_id=101, starts_at=kst(9, 23, 16))
    records.seed(record(photographed.id, media=((51, "photo", "before", 0),)))
    records.seed(record(noted.id, care_note="메모만"))
    view = await _day(interactor, date(2026, 9, 23))
    assert [(i.has_record, i.cover) for i in view.items] == [(True, "t/51"), (True, None), (False, None)]


async def test_알림장을_보낸_방문을_알리고_링크는_한_번에_읽는다():
    visits, directory = FakeVisits(), FakeDirectory()
    directory.family(1, pets=(101,))
    reports = FakeReportRepository(visits)
    interactor = ListDayVisitsInteractor(visits, FakeMenus(), FakeSchedule(), directory, FakeRecords(visits),
                                         FakeLibrary(), reports, now=lambda: NOW, checks=FakeChecks(),
                                         revisit_settings=FakeRevisitSettingsRepository())
    sent, expired, revoked, *_ = [
        visits.seed(pet_id=101, starts_at=kst(9, 22, hour), status="completed", started_at=kst(9, 22, hour),
                    completed_at=kst(9, 22, hour + 1))
        for hour in (10, 12, 14, 16, 18)
    ]
    sent_at = NOW - timedelta(hours=3)
    await reports.create(ctx(), sent.id, bytes(16), NOW + timedelta(days=7), sent_at)
    await reports.create(ctx(), expired.id, bytes(16), NOW, sent_at)   # 지금 끝난다
    await reports.create(ctx(), revoked.id, bytes(16), None, sent_at)
    await reports.revoke(ctx(), revoked.id, NOW)
    view = await _day(interactor, date(2026, 9, 22))
    assert [i.report_sent for i in view.items] == [True, False, False, False, False]
    # 방문이 다섯이어도 살아 있는 링크 한 번, 보낸 적이 있는지 한 번(⑬ — 남은 일 '알림장 안 보냄').
    assert reports.reads == ["live_visit_ids", "visit_ids_with_report"]
