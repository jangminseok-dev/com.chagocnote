import pytest

from hub.app.dtos.pet_revisit import PetRevisitFact
from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery
from visit.app.use_cases.get_next_visit_draft_interactor import GetNextVisitDraftInteractor
from visit.domain.errors import VisitNotFoundError, VisitStateConflictError
from visit.domain.value_objects.revisit_settings import RevisitSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeRevisitSettingsRepository, FakeVisits

NOW = kst(9, 23, 18)


def _setup():
    visits, menus, directory, settings = FakeVisits(), FakeMenus(), FakeDirectory(), FakeRevisitSettingsRepository()
    interactor = GetNextVisitDraftInteractor(
        visits, visits, menus, directory=directory, settings=settings, now=lambda: NOW)
    return visits, menus, directory, settings, interactor


def _done(visits, **fields):
    starts = fields.pop("starts_at")
    return visits.seed(status="completed", starts_at=starts, started_at=starts, completed_at=starts, **fields)


async def _draft(interactor, visit_id):
    return await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=visit_id))


async def test_계산한_주기_뒤_같은_요일_시각_같은_메뉴다():
    visits, menus, _, _, interactor = _setup()
    trim = menus.seed("전체 미용")
    _done(visits, pet_id=101, starts_at=kst(7, 15, 14))
    _done(visits, pet_id=101, starts_at=kst(8, 19, 14))
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14), duration_minutes=150, menu_ids=(trim.id,))
    draft = await _draft(interactor, kong.id)
    assert (draft.cycle_weeks, draft.cycle_source, draft.interval_weeks) == (5, "computed", 5)   # 35·35일 → 5주
    assert (draft.customer_id, draft.pet_ids, draft.duration_minutes, [m.name for m in draft.menus]) == (
        1, [101], 150, ["전체 미용"])
    assert draft.starts_at.isoformat() == "2026-10-28T14:00:00+09:00"


async def test_가족이면_아이들_가운데_짧은_주기이고_완료하지_않은_아이는_빠진다():
    visits, _, _, _, interactor = _setup()
    for day in ((7, 15), (8, 19)):
        _done(visits, pet_id=101, starts_at=kst(*day, 14))     # 5주마다
    for day in ((8, 12), (9, 2)):
        _done(visits, pet_id=102, starts_at=kst(*day, 14))     # 3주마다
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14))
    _done(visits, pet_id=102, starts_at=kst(9, 23, 14))
    visits.seed(pet_id=103, starts_at=kst(9, 23, 14), status="no_show")
    draft = await _draft(interactor, kong.id)
    assert (draft.pet_ids, draft.cycle_weeks, draft.cycle_source) == ([101, 102], 3, "computed")
    assert draft.starts_at.isoformat() == "2026-10-14T14:00:00+09:00"


async def test_한_번뿐이면_매장의_기본_간격으로_어림하고_날짜가_늘_있다():
    visits, _, _, settings, interactor = _setup()
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14))
    draft = await _draft(interactor, kong.id)
    assert (draft.cycle_weeks, draft.cycle_source, draft.starts_at.isoformat()) == (
        4, "none", "2026-10-21T14:00:00+09:00")
    settings.rows[1] = RevisitSettings(default_cycle_weeks=6)
    assert (await _draft(interactor, kong.id)).cycle_weeks == 6


async def test_간격_하나는_주기가_아니라_어림이다():
    visits, _, _, _, interactor = _setup()
    _done(visits, pet_id=101, starts_at=kst(9, 9, 14))
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14))   # 2주 만에 — 주기로 쓰지 않는다
    draft = await _draft(interactor, kong.id)
    assert (draft.cycle_weeks, draft.cycle_source) == (4, "single")


async def test_직접_정한_주기가_앞선다():
    visits, _, directory, _, interactor = _setup()
    directory.revisits[101] = PetRevisitFact(grooming_cycle_weeks=8, revisit_nudged_on=None)
    for day in ((8, 12), (9, 2)):
        _done(visits, pet_id=101, starts_at=kst(*day, 14))
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14))
    draft = await _draft(interactor, kong.id)
    assert (draft.cycle_weeks, draft.cycle_source, draft.starts_at.isoformat()) == (
        8, "manual", "2026-11-18T14:00:00+09:00")


async def test_보호자만의_방문이면_반려동물_없이_매장의_기본_간격이다():
    visits, _, directory, _, interactor = _setup()
    solo = _done(visits, pet_id=None, starts_at=kst(9, 23, 14))
    draft = await _draft(interactor, solo.id)
    assert (draft.pet_ids, draft.cycle_weeks, draft.cycle_source) == ([], 4, "none")
    assert directory.revisit_calls == []   # 아이가 없으면 묻지 않는다


async def test_완료_전_방문도_초안을_준다__이번_방문을_이번으로_놓고_계산한다():
    visits, _, _, _, interactor = _setup()
    _done(visits, pet_id=101, starts_at=kst(7, 1, 14))
    _done(visits, pet_id=101, starts_at=kst(8, 12, 14))
    now = visits.seed(pet_id=101, starts_at=kst(9, 23, 14), status="in_progress", started_at=kst(9, 23, 14))
    visits.seed(pet_id=103, starts_at=kst(9, 23, 14), status="canceled", canceled_at=kst(9, 23, 9),
                cancel_reason="shop_reason")
    draft = await _draft(interactor, now.id)
    assert (draft.cycle_weeks, draft.cycle_source, draft.pet_ids) == (6, "computed", [101])   # 42·42일
    assert draft.starts_at.isoformat() == "2026-11-04T14:00:00+09:00"


async def test_예약됨_방문은_완료가_없으면_매장의_기본_간격이다():
    visits, _, _, _, interactor = _setup()
    reserved = visits.seed(pet_id=101, starts_at=kst(9, 30, 14))
    draft = await _draft(interactor, reserved.id)
    assert (draft.cycle_weeks, draft.cycle_source, draft.starts_at.isoformat()) == (
        4, "none", "2026-10-28T14:00:00+09:00")


async def test_취소_노쇼한_방문이나_다른_매장_방문은_안_된다():
    visits, _, _, _, interactor = _setup()
    canceled = visits.seed(pet_id=101, starts_at=kst(9, 30, 14), status="canceled", canceled_at=kst(9, 29, 9),
                           cancel_reason="customer_request")
    with pytest.raises(VisitStateConflictError):
        await _draft(interactor, canceled.id)
    theirs = _done(visits, pet_id=201, starts_at=kst(9, 23, 14), shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(shop_id=1), visit_id=theirs.id))
