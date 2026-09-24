import pytest

from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery
from visit.app.use_cases.get_next_visit_draft_interactor import GetNextVisitDraftInteractor
from visit.domain.errors import VisitNotFoundError, VisitStateConflictError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeMenus, FakeVisits


def _setup():
    visits, menus = FakeVisits(), FakeMenus()
    return visits, menus, GetNextVisitDraftInteractor(visits, visits, menus)


def _done(visits, **fields):
    starts = fields.pop("starts_at")
    return visits.seed(status="completed", starts_at=starts, started_at=starts, completed_at=starts, **fields)


async def test_주기_뒤_같은_요일_시각_같은_메뉴로_가족_전체():
    visits, menus, interactor = _setup()
    trim = menus.seed("전체 미용")
    _done(visits, pet_id=101, starts_at=kst(8, 19, 14))
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14), duration_minutes=150, menu_ids=(trim.id,))
    _done(visits, pet_id=102, starts_at=kst(9, 23, 14))
    visits.seed(pet_id=103, starts_at=kst(9, 23, 14), status="no_show")   # 같은 묶음이라도 완료가 아니면 빠진다
    draft = await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=kong.id))
    assert draft.interval_weeks == 5   # 8/19 → 9/23 은 5주
    assert (draft.customer_id, draft.pet_ids, draft.duration_minutes, [m.name for m in draft.menus]) == (
        1, [101, 102], 150, ["전체 미용"])
    assert draft.starts_at.isoformat() == "2026-10-28T14:00:00+09:00"


async def test_처음_완료했으면_4주_뒤다():
    visits, _, interactor = _setup()
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14))
    draft = await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=kong.id))
    assert (draft.interval_weeks, draft.starts_at.isoformat()) == (4, "2026-10-21T14:00:00+09:00")


async def test_보호자만의_방문이면_반려동물_없이():
    visits, _, interactor = _setup()
    solo = _done(visits, pet_id=None, starts_at=kst(9, 23, 14))
    draft = await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=solo.id))
    assert draft.pet_ids == []


async def test_완료_전_방문도_초안을_준다__이번_방문과_직전_완료의_간격으로():
    visits, _, interactor = _setup()
    _done(visits, pet_id=101, starts_at=kst(8, 12, 14))
    now = visits.seed(pet_id=101, starts_at=kst(9, 23, 14), status="in_progress", started_at=kst(9, 23, 14))
    visits.seed(pet_id=102, starts_at=kst(9, 23, 14), status="in_progress", started_at=kst(9, 23, 14))
    visits.seed(pet_id=103, starts_at=kst(9, 23, 14), status="canceled", canceled_at=kst(9, 23, 9),
                cancel_reason="shop_reason")   # 취소한 아이는 빠진다
    draft = await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=now.id))
    assert (draft.interval_weeks, draft.pet_ids, draft.starts_at.isoformat()) == (
        6, [101, 102], "2026-11-04T14:00:00+09:00")   # 8/12 → 9/23 은 6주(이번 방문을 "이번"으로 놓아야 판별된다)


async def test_예약됨_방문은_직전_완료가_없으면_4주_뒤다():
    visits, _, interactor = _setup()
    reserved = visits.seed(pet_id=101, starts_at=kst(9, 30, 14))
    draft = await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=reserved.id))
    assert (draft.interval_weeks, draft.starts_at.isoformat()) == (4, "2026-10-28T14:00:00+09:00")


async def test_취소_노쇼한_방문이나_다른_매장_방문은_안_된다():
    visits, _, interactor = _setup()
    canceled = visits.seed(pet_id=101, starts_at=kst(9, 30, 14), status="canceled", canceled_at=kst(9, 29, 9),
                           cancel_reason="customer_request")
    with pytest.raises(VisitStateConflictError):
        await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=canceled.id))
    theirs = _done(visits, pet_id=201, starts_at=kst(9, 23, 14), shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(shop_id=1), visit_id=theirs.id))
