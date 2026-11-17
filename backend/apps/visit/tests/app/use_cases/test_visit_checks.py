"""확인할 것(③-B) — 조립(호출 수), 미리 보기, 방문 상세, 하루 목록. 지금은 2026-11-14 15시(한국)다."""
from datetime import date, timedelta

import pytest

from hub.app.dtos.care_facts import CautionFact, ConditionFact, PetCareFact
from hub.app.errors import FamilyNotFoundError
from visit.app.dtos.get_visit_checks_dto import GetVisitChecksQuery
from visit.app.dtos.get_visit_dto import GetVisitQuery
from visit.app.dtos.list_day_visits_dto import ListDayVisitsQuery
from visit.app.services.visit_checks import CheckTarget, read_checks
from visit.app.use_cases.get_visit_checks_interactor import GetVisitChecksInteractor
from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
from visit.app.use_cases.list_day_visits_interactor import ListDayVisitsInteractor
from visit.domain.errors import VisitInputError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import (
    FakeRevisitSettingsRepository,
    FakeChecks,
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeSchedule,
    FakeSeries,
    FakeVisits,
)

NOW = kst(11, 14, 15)
TODAY = date(2026, 11, 14)


def _senior(pet_id=101, customer_id=1, conditions=(), consent_on=None, passed_away=False) -> PetCareFact:
    return PetCareFact(pet_id=pet_id, customer_id=customer_id, birth_date=None, birth_year=2010,
                       conditions=tuple(conditions), consent_on=consent_on, passed_away=passed_away)


def _world():
    directory, checks = FakeDirectory(), FakeChecks()
    directory.family(1, pets=(101, 102))
    directory.family(2, pets=(201,), name="박두부")
    return directory, checks


def _codes(found) -> list[str]:
    return [c.code for c in found]


def _target(key, customer_id=1, pet_id=101, at=None) -> CheckTarget:
    at = at or kst(11, 14, 10)
    return CheckTarget(key=key, customer_id=customer_id, pet_id=pet_id, on=TODAY, before=at)


# ── 조립

async def test_사실을_모아_판정에_넘긴다():
    directory, checks = _world()
    directory.cautions[1] = CautionFact(reason="입질", until=date(2027, 1, 1))
    directory.pet_facts[101] = _senior(conditions=[ConditionFact("심장 질환", "약 복용")])
    checks.completed[101] = [kst(3, 1, 10)]              # 258일 전
    checks.no_show_starts[1] = [kst(10, 1, 10)]

    read = await read_checks(ctx(), [_target(7)], directory, checks, TODAY)

    found = read.by_key[7]
    assert _codes(found) == ["caution", "no_show", "consent", "conditions", "long_absence"]
    assert found[4].detail == {"days": 258, "last_visit_on": date(2026, 3, 1)}
    assert (read.known_customers, read.known_pets) == ({1}, {101})


@pytest.mark.parametrize("count", [1, 30])
async def test_방문이_몇_개든_포트_한_번_저장소_메서드_한_번씩이다(count):
    directory, checks = _world()
    targets = [
        _target(key, customer_id=1 if key % 2 else 2, pet_id=(101, 201, None)[key % 3],
                at=kst(11, 14, 9) + timedelta(minutes=10 * key))
        for key in range(1, count + 1)
    ]

    read = await read_checks(ctx(), targets, directory, checks, TODAY)

    assert len(directory.care_calls) == 1
    assert [name for name, _ in checks.calls] in (["last_completed", "no_shows"], ["no_shows"])
    assert set(read.by_key) == {t.key for t in targets}
    customers, pets, today = directory.care_calls[0]
    assert (customers, today) == (tuple(sorted({t.customer_id for t in targets})), TODAY)
    assert pets == tuple(sorted({t.pet_id for t in targets if t.pet_id is not None}))   # 겹치는 ID 는 한 번만


async def test_보호자만의_방문뿐이면_이력을_묻지_않는다():
    directory, checks = _world()
    read = await read_checks(ctx(), [_target(1, pet_id=None)], directory, checks, TODAY)
    assert checks.calls == [("no_shows", 1)]
    assert read.by_key == {1: []}


async def test_대상이_없으면_아무것도_읽지_않는다():
    directory, checks = _world()
    read = await read_checks(ctx(), [], directory, checks, TODAY)
    assert (read.by_key, directory.care_calls, checks.calls) == ({}, [], [])


async def test_익명화했거나_다른_매장인_고객의_방문에는_아무것도_없다():
    directory, checks = _world()
    directory.family(9, pets=(901,), shop_id=2)
    checks.no_show_starts[9] = [kst(10, 1, 10)]

    read = await read_checks(ctx(shop_id=1), [_target(1, customer_id=9, pet_id=901)], directory, checks, TODAY)

    assert read.by_key == {1: []}
    assert 9 not in read.known_customers


async def test_노쇼는_방문_날_앞_365일의_것만_센다():
    directory, checks = _world()
    checks.completed[101] = [kst(11, 1, 10)]
    start_of_window = kst(11, 14, 0) - timedelta(days=365)     # 2025-11-14 0시(한국)
    checks.no_show_starts[1] = [
        start_of_window,                                # 창의 첫 순간 — 센다
        start_of_window - timedelta(minutes=10),        # 하루 앞 — 안 센다
        kst(11, 14, 9),                                 # 오늘 앞서 — 센다
        kst(11, 14, 10),                                # 이 방문과 같은 시각 — 안 센다
        kst(11, 20, 10),                                # 뒤 — 안 센다
    ]

    read = await read_checks(ctx(), [_target(1)], directory, checks, TODAY)

    assert [(c.code, c.detail) for c in read.by_key[1]] == [("no_show", {"count": 2})]


async def test_자정_앞뒤의_완료_방문은_매장_시간대의_날로_센다():
    directory, checks = _world()
    # 한국 5월 18일 0시 30분(UTC 로는 17일) — 11월 14일까지 180일이라 오랜만이 아니다. UTC 날짜로 세면 181일이 된다.
    checks.completed[101] = [kst(5, 18, 0, 30)]
    read = await read_checks(ctx(), [_target(1)], directory, checks, TODAY)
    assert read.by_key[1] == []


# ── 미리 보기

def _preview(directory, checks):
    return GetVisitChecksInteractor(directory, checks, now=lambda: NOW)


async def _ask(interactor, customer_id=1, pet_ids=(101,), day=TODAY, shop_id=1):
    return await interactor.get_visit_checks(
        GetVisitChecksQuery(ctx=ctx(shop_id=shop_id), customer_id=customer_id, pet_ids=tuple(pet_ids), day=day)
    )


async def test_미리_보기는_보호자_항목을_한_번_아이_항목을_아이마다_준다():
    directory, checks = _world()
    directory.cautions[1] = CautionFact(reason="노쇼 2번", until=date(2027, 1, 1))
    directory.pet_facts[102] = _senior(pet_id=102)
    checks.completed[101] = [kst(11, 1, 10)]

    view = await _ask(_preview(directory, checks), pet_ids=(101, 102))

    assert _codes(view.customer) == ["caution"]
    assert [(p.pet_id, _codes(p.checks)) for p in view.pets] == [(101, []), (102, ["first_visit", "consent"])]
    assert len(directory.care_calls) == 1


async def test_아이를_고르지_않으면_보호자_항목만_있다():
    directory, checks = _world()
    checks.no_show_starts[1] = [kst(10, 1, 10)]
    view = await _ask(_preview(directory, checks), pet_ids=())
    assert (_codes(view.customer), view.pets) == (["no_show"], [])


async def test_그날_앞서_끝낸_방문도_이력이라_첫_방문이_아니다():
    directory, checks = _world()
    checks.completed[101] = [kst(11, 14, 9)]
    view = await _ask(_preview(directory, checks))
    assert view.pets[0].checks == []


async def test_예약할_날을_기준으로_센다():
    directory, checks = _world()
    directory.pet_facts[101] = PetCareFact(pet_id=101, customer_id=1, birth_date=date(2016, 12, 1), birth_year=None,
                                           conditions=(), consent_on=None, passed_away=False)
    checks.completed[101] = [kst(11, 1, 10)]
    interactor = _preview(directory, checks)

    assert (await _ask(interactor, day=date(2026, 11, 30))).pets[0].checks == []
    assert _codes((await _ask(interactor, day=date(2026, 12, 1))).pets[0].checks) == ["consent"]


async def test_없거나_익명화했거나_다른_매장의_고객은_404_다():
    directory, checks = _world()
    interactor = _preview(directory, checks)
    with pytest.raises(FamilyNotFoundError):
        await _ask(interactor, customer_id=999)
    with pytest.raises(FamilyNotFoundError):
        await _ask(interactor, customer_id=1, shop_id=2)


async def test_그_보호자의_아이가_아닌_것은_빠지고_겹쳐_준_것은_한_번이다():
    directory, checks = _world()
    view = await _ask(_preview(directory, checks), pet_ids=(101, 201, 101, 999))
    assert [p.pet_id for p in view.pets] == [101]


async def test_열한_마리와_예약_범위_밖의_날은_422_다():
    directory, checks = _world()
    interactor = _preview(directory, checks)
    with pytest.raises(VisitInputError):
        await _ask(interactor, pet_ids=tuple(range(1, 12)))
    await _ask(interactor, day=TODAY + timedelta(days=366))
    await _ask(interactor, day=TODAY - timedelta(days=366))
    for off in (367, -367):
        with pytest.raises(VisitInputError):
            await _ask(interactor, day=TODAY + timedelta(days=off))
    assert len(directory.care_calls) == 2   # 거절한 물음은 읽지 않는다


# ── 방문 상세

def _detail(visits, directory, checks):
    return GetVisitInteractor(
        visits, visits, visits, FakeMenus(), directory, FakeRecords(visits), FakeLibrary(),
        FakeReportRepository(visits), now=lambda: NOW, link_key=bytes(range(32)),
        web_base_url="https://r.example", checks=checks, series=FakeSeries(),
    )


async def test_방문_상세에_확인할_것이_실린다():
    directory, checks = _world()
    visits = FakeVisits()
    directory.pet_facts[101] = _senior(conditions=[ConditionFact("심장 질환", None)], consent_on=date(2026, 3, 1))
    checks.completed[101] = [kst(10, 20, 10)]
    visit = visits.seed(customer_id=1, pet_id=101, starts_at=kst(11, 20, 10))

    detail = await _detail(visits, directory, checks).get_visit(GetVisitQuery(ctx=ctx(), visit_id=visit.id))

    assert [(c.code, c.scope) for c in detail.checks] == [("conditions", "pet")]
    assert detail.checks[0].detail == {"items": [{"label": "심장 질환", "note": None}]}


async def test_미용_중인_첫_방문도_첫_방문이다():
    directory, checks = _world()
    visits = FakeVisits()
    visit = visits.seed(customer_id=1, pet_id=101, starts_at=kst(11, 14, 10), status="in_progress",
                        started_at=kst(11, 14, 10))
    checks.completed[101] = [kst(11, 20, 10)]   # 뒤의 방문은 이력이 아니다

    detail = await _detail(visits, directory, checks).get_visit(GetVisitQuery(ctx=ctx(), visit_id=visit.id))

    assert _codes(detail.checks) == ["first_visit"]


@pytest.mark.parametrize("status,extra", [
    ("completed", dict(started_at=kst(11, 14, 10), completed_at=kst(11, 14, 11))),
    ("canceled", dict(canceled_at=kst(11, 14, 9), cancel_reason="customer_request")),
    ("no_show", {}),
])
async def test_살아_있지_않은_방문에는_확인할_것이_없고_읽지도_않는다(status, extra):
    directory, checks = _world()
    visits = FakeVisits()
    directory.cautions[1] = CautionFact(reason="입질", until=date(2027, 1, 1))
    visit = visits.seed(customer_id=1, pet_id=101, starts_at=kst(11, 14, 10), status=status, **extra)

    detail = await _detail(visits, directory, checks).get_visit(GetVisitQuery(ctx=ctx(), visit_id=visit.id))

    assert detail.checks == []
    assert (directory.care_calls, checks.calls) == ([], [])


# ── 하루 목록

def _board(visits, directory, checks):
    return ListDayVisitsInteractor(visits, FakeMenus(), FakeSchedule(), directory, FakeRecords(visits),
                                   FakeLibrary(), FakeReportRepository(visits), now=lambda: NOW, checks=checks,
                                   revisit_settings=FakeRevisitSettingsRepository())


async def test_하루_목록은_방문마다_보호자_항목과_아이_항목의_수를_준다():
    directory, checks = _world()
    visits = FakeVisits()
    directory.cautions[1] = CautionFact(reason="입질", until=date(2027, 1, 1))
    directory.pet_facts[101] = _senior(conditions=[ConditionFact("심장 질환", None)])   # 동의 필요 + 지병(안 셈)
    checks.completed[101] = [kst(11, 1, 10)]
    checks.completed[201] = [kst(11, 1, 10)]
    checks.no_show_starts[1] = [kst(10, 1, 10)]
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(11, 14, 16))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(11, 14, 16))            # 가족 묶음 — 첫 방문
    dubu = visits.seed(customer_id=2, pet_id=201, starts_at=kst(11, 14, 17))            # 확인할 것 없음
    done = visits.seed(customer_id=1, pet_id=101, starts_at=kst(11, 14, 9), status="completed",
                       started_at=kst(11, 14, 9), completed_at=kst(11, 14, 10))

    day = await _board(visits, directory, checks).list_day_visits(ListDayVisitsQuery(ctx=ctx(), day=TODAY))

    counts = {i.visit.visit_id: (i.customer_check_count, i.pet_check_count) for i in day.items}
    assert counts == {kong.id: (2, 1), bori.id: (2, 1), dubu.id: (0, 0), done.id: (0, 0)}
    assert len(directory.care_calls) == 1
    assert checks.calls == [("last_completed", 3), ("no_shows", 3)]   # 살아 있는 방문 셋만 묻는다


async def test_방문이_없는_날은_확인할_것을_읽지_않는다():
    directory, checks = _world()
    day = await _board(FakeVisits(), directory, checks).list_day_visits(ListDayVisitsQuery(ctx=ctx(), day=TODAY))
    assert (day.items, directory.care_calls, checks.calls) == ([], [], [])
