from datetime import date, time

import pytest

from hub.app.dtos.visit_events import VisitReserved
from hub.app.errors import FamilyPetNotFoundError
from visit.app.dtos.register_visit_dto import RegisterVisitCommand, RepeatRequest
from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
from visit.domain.errors import (
    MenuNotAvailableError,
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitInputError,
)
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeEvents,
    FakeMenus,
    FakeSchedule,
    FakeSeries,
    FakeVisits,
    Journal,
)

NOW = kst(9, 23, 15, 37)


def _setup(settings=None):
    journal = Journal()
    schedule = FakeSchedule(journal) if settings is None else FakeSchedule(journal, settings)
    menus, visits, directory = FakeMenus(journal), FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102))
    events = FakeEvents(journal)
    interactor = RegisterVisitInteractor(visits, visits, menus, schedule, directory, events=events, now=lambda: NOW,
                                         series=FakeSeries(journal))
    return journal, schedule, menus, visits, directory, interactor, events


def _command(**overrides):
    fields = dict(ctx=ctx(), customer_id=1, pet_ids=(101,), starts_at=kst(10, 2, 14), duration_minutes=None,
                  menu_ids=(), memo=None, walk_in=False)
    fields.update(overrides)
    return RegisterVisitCommand(**fields)


async def test_두_마리면_방문이_둘이고_가족을_잠근_뒤_넣는다():
    journal, _, menus, _, _, interactor, _ = _setup()
    bath = menus.seed("목욕", minutes=60)
    nails = menus.seed("발톱", minutes=None)   # 기본 소요가 없으면 매장 기본(120)으로 센다
    result = await interactor.register_visit(_command(pet_ids=(101, 102), menu_ids=(bath.id, nails.id)))
    assert [(v.pet.pet_id, v.status, v.duration_minutes) for v in result.visits] == [
        (101, "reserved", 180), (102, "reserved", 180)]
    assert [m.name for m in result.visits[0].menus] == ["목욕", "발톱"]
    assert result.warnings == []   # 형제끼리는 겹침이 아니다
    names = [entry[0] for entry in journal]
    assert names.index("lock_family") < names.index("create_visits")
    assert ("lock_family", 1, (101, 102)) in journal


async def test_시각은_매장_시간대로_내보낸다():
    *_, interactor, _ = _setup()
    [visit] = (await interactor.register_visit(_command())).visits
    assert (visit.starts_at.isoformat(), visit.ends_at.isoformat()) == (
        "2026-10-02T14:00:00+09:00", "2026-10-02T16:00:00+09:00")
    assert (visit.customer.name, visit.pet.name) == ("김민지", "아이101")


async def test_반려동물_없이_보호자만의_방문_하나():
    *_, visits, _, interactor, _ = _setup()
    [visit] = (await interactor.register_visit(_command(pet_ids=()))).visits
    assert visit.pet is None
    assert visits.rows[visit.visit_id].pet_id is None


async def test_메뉴도_소요도_없으면_매장_기본_소요다():
    *_, interactor, _ = _setup(ScheduleSettings(time(10), time(19), 90, frozenset()))
    [visit] = (await interactor.register_visit(_command())).visits
    assert visit.duration_minutes == 90


async def test_소요를_보내면_그_값이다():
    *_, interactor, _ = _setup()
    [visit] = (await interactor.register_visit(_command(duration_minutes=150))).visits
    assert visit.duration_minutes == 150


async def test_지금_시작한_손님은_10분_단위로_내린_시각에_미용_중이다():
    *_, visits, _, interactor, _ = _setup()
    [visit] = (await interactor.register_visit(_command(starts_at=None, walk_in=True))).visits
    row = visits.rows[visit.visit_id]
    assert (row.starts_at, row.status, row.started_at, row.status_changed_by_member_id) == (
        kst(9, 23, 15, 30), "in_progress", NOW, 11)


@pytest.mark.parametrize("fields", [dict(walk_in=True), dict(starts_at=None)])
async def test_예약_시각과_지금_시작은_하나만(fields):
    journal, *_, interactor, _ = _setup()
    with pytest.raises(VisitInputError):
        await interactor.register_visit(_command(**fields))
    assert journal == []


async def test_고를_수_없는_메뉴면_잠그지도_않는다():
    """V1 — 다른 매장 메뉴와 보관한 메뉴는 이 매장에 없는 메뉴다."""
    journal, _, menus, *_, interactor, _ = _setup()
    theirs = menus.seed("남의 메뉴", shop_id=2)
    archived = menus.seed("옛 메뉴", archived=True)
    for menu_id in (theirs.id, archived.id, 999):
        with pytest.raises(MenuNotAvailableError):
            await interactor.register_visit(_command(menu_ids=(menu_id,)))
    assert "lock_family" not in [entry[0] for entry in journal]


@pytest.mark.parametrize(("fields", "error"), [
    (dict(starts_at=kst(10, 2, 14, 5)), VisitInputError),                  # 10분 단위가 아니다
    (dict(starts_at=kst(10, 2, 23), duration_minutes=120), VisitCrossesMidnightError),
    (dict(duration_minutes=95), VisitInputError),
])
async def test_시각_규칙에_어긋나면_잠그지도_않는다(fields, error):
    journal, *_, interactor, _ = _setup()
    with pytest.raises(error):
        await interactor.register_visit(_command(**fields))
    assert "lock_family" not in [entry[0] for entry in journal]


async def test_가족_확인에서_거절되면_넣지_않는다():
    """V2 — 다른 가족·다른 매장의 반려동물, 무지개다리 아이는 customer 가 거절한다."""
    journal, *_, interactor, _ = _setup()
    with pytest.raises(FamilyPetNotFoundError):
        await interactor.register_visit(_command(pet_ids=(999,)))
    assert "create_visits" not in [entry[0] for entry in journal]


async def test_같은_시각에_이미_있으면_VISIT_DUPLICATE_다():
    *_, interactor, _ = _setup()
    await interactor.register_visit(_command())
    with pytest.raises(VisitDuplicateError):
        await interactor.register_visit(_command())


async def test_경고는_막지_않고_함께_돌려준다():
    _, _, _, visits, directory, interactor, _ = _setup(
        ScheduleSettings(time(10), time(19), 120, frozenset({4})))   # 금요일 휴무
    directory.family(2, pets=(201,))
    visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 13), duration_minutes=120)
    result = await interactor.register_visit(_command(starts_at=kst(10, 2, 18)))   # 10/2 는 금요일
    assert result.warnings == ["closed_day", "outside_hours"]
    result = await interactor.register_visit(_command(pet_ids=(102,), starts_at=kst(10, 2, 14)))
    assert result.warnings == ["overlap", "closed_day"]


async def test_임시_휴무일도_closed_day():
    _, schedule, *_, interactor, _ = _setup()
    schedule.closed[(1, date(2026, 10, 2))] = ClosedDate(day=date(2026, 10, 2), note=None)
    assert (await interactor.register_visit(_command())).warnings == ["closed_day"]


async def test_예약마다_VisitReserved_를_넣은_뒤에_발행한다():
    journal, _, _, _, _, interactor, events = _setup()
    result = await interactor.register_visit(_command(pet_ids=(101, 102)))
    assert [(type(e), e.ctx, e.visit_id, e.customer_id, e.pet_id, e.starts_at, e.occurred_at, e.revived,
             e.family_pet_ids)
            for e in events.published] == [
        (VisitReserved, ctx(), v.visit_id, 1, pet_id, kst(10, 2, 14), NOW, False, (101, 102))
        for v, pet_id in zip(result.visits, (101, 102))]
    names = [entry[0] for entry in journal]
    assert names.index("create_visits") < names.index("publish")


async def test_보호자만의_방문은_가족_묶음이_비어_있다():
    *_, interactor, events = _setup()
    await interactor.register_visit(_command(pet_ids=()))
    [event] = events.published
    assert (event.pet_id, event.family_pet_ids) == (None, ())


async def test_지금_시작한_손님은_예약이_아니라_발행하지_않는다():
    *_, interactor, events = _setup()
    await interactor.register_visit(_command(starts_at=None, walk_in=True))
    assert events.published == []


async def test_등록이_실패하면_발행하지_않는다():
    *_, interactor, events = _setup()
    with pytest.raises(MenuNotAvailableError):
        await interactor.register_visit(_command(menu_ids=(999,)))
    assert events.published == []


async def test_만든_방문마다_다시_색인하라고_알린다():
    """메모가 없어도 알린다 — 문서가 될지는 색인기가 읽어 보고 정한다. 지금 시작한 손님도 같다."""
    _, _, _, _, _, interactor, events = _setup()
    booked = await interactor.register_visit(_command(pet_ids=(101, 102), memo="발톱 짧게"))
    walk_in = await interactor.register_visit(_command(pet_ids=(), starts_at=None, walk_in=True))
    assert events.changed == [("visit", v.visit_id) for v in (*booked.visits, *walk_in.visits)]


# --- ⑭ 반복 예약 -----------------------------------------------------------------------------------------------------

def _repeat(**overrides):
    return _command(pet_ids=(101, 102), repeat=RepeatRequest(**({"interval_weeks": 4, "count": 3} | overrides)))


async def test_반복이면_회차마다_가족_방문을_만들고_같은_묶음에_넣는다():
    journal, _, _, visits, _, interactor, _ = _setup()
    result = await interactor.register_visit(_repeat())
    rows = sorted(visits.rows.values(), key=lambda v: (v.starts_at, v.id))
    assert [(v.starts_at, v.pet_id) for v in rows] == [
        (kst(10, 2, 14), 101), (kst(10, 2, 14), 102), (kst(10, 30, 14), 101), (kst(10, 30, 14), 102),
        (kst(11, 27, 14), 101), (kst(11, 27, 14), 102)]
    assert {v.series_id for v in rows} == {result.series.id}
    names = [entry[0] for entry in journal]
    assert names.index("lock_family") < names.index("create_series") < names.index("create_visits")
    assert ("create_series", 1, 4) in journal
    assert len(result.visits) == 6
    assert result.series.interval_weeks == 4
    assert [o.starts_at.isoformat() for o in result.series.occurrences] == [
        "2026-10-02T14:00:00+09:00", "2026-10-30T14:00:00+09:00", "2026-11-27T14:00:00+09:00"]
    assert result.warnings == result.series.occurrences[0].warnings


async def test_첫_회차만_접수_안내이고_나머지는_리마인드만():
    _, _, _, _, _, interactor, events = _setup()
    await interactor.register_visit(_repeat())
    assert [(e.starts_at, e.series_followup, e.family_pet_ids) for e in events.published] == [
        (kst(10, 2, 14), False, (101, 102)), (kst(10, 2, 14), False, (101, 102)),
        (kst(10, 30, 14), True, (101, 102)), (kst(10, 30, 14), True, (101, 102)),
        (kst(11, 27, 14), True, (101, 102)), (kst(11, 27, 14), True, (101, 102))]


async def test_첫_회차를_빼면_둘째_회차가_접수_안내를_받는다():
    _, _, _, visits, _, interactor, events = _setup()
    await interactor.register_visit(_repeat(skip=(1,)))
    assert sorted({v.starts_at for v in visits.rows.values()}) == [kst(10, 30, 14), kst(11, 27, 14)]
    assert [(e.starts_at, e.series_followup) for e in events.published][::2] == [
        (kst(10, 30, 14), False), (kst(11, 27, 14), True)]


async def test_빼고_남은_회차가_하나면_VISIT_INPUT():
    _, _, _, visits, _, interactor, _ = _setup()
    with pytest.raises(VisitInputError):
        await interactor.register_visit(_repeat(count=2, skip=(2,)))
    assert visits.rows == {}


async def test_지금_시작에는_반복을_싣지_못한다():
    _, _, _, _, _, interactor, _ = _setup()
    with pytest.raises(VisitInputError):
        await interactor.register_visit(_command(starts_at=None, walk_in=True,
                                                 repeat=RepeatRequest(interval_weeks=4, count=3)))


async def test_1년을_넘는_회차는_조용히_빠진다():
    _, _, _, visits, _, interactor, _ = _setup()
    result = await interactor.register_visit(_command(repeat=RepeatRequest(interval_weeks=12, count=6)))
    assert len(result.series.occurrences) == 5
    assert len(visits.rows) == 5


async def test_방문마다_검색_이벤트를_낸다():
    _, _, _, visits, _, interactor, events = _setup()
    await interactor.register_visit(_repeat())
    assert sorted(ref for _, ref in events.changed) == sorted(visits.rows)


async def test_회차가_이미_예약된_시각이면_전부_VISIT_DUPLICATE():
    _, _, _, visits, _, interactor, events = _setup()
    taken = visits.seed(pet_id=101, starts_at=kst(10, 30, 14))
    with pytest.raises(VisitDuplicateError):
        await interactor.register_visit(_repeat())
    assert list(visits.rows) == [taken.id]
    assert events.published == []


async def test_repeat_없는_예전_요청은_묶음_없이_지금처럼():
    journal, _, _, visits, _, interactor, events = _setup()
    result = await interactor.register_visit(_command())
    assert result.series is None
    assert [v.series_id for v in visits.rows.values()] == [None]
    assert [e.series_followup for e in events.published] == [False]
    assert "create_series" not in [entry[0] for entry in journal]
