from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeVisits

NOW = kst(9, 23, 15)


def _ledger():
    visits = FakeVisits()
    return visits, VisitLedgerInteractor(visits, now=lambda: NOW)


async def test_반려동물의_방문과_앞으로의_예약():
    visits, ledger = _ledger()
    visits.seed(pet_id=101, status="canceled", canceled_at=NOW, cancel_reason="shop_reason")
    visits.seed(pet_id=102, starts_at=kst(9, 20, 10))   # 정리 안 된 지난 예약도 앞으로의 예약이다
    visits.seed(pet_id=103, shop_id=2)
    assert (await ledger.pet_has_visits(ctx(), 101), await ledger.pet_has_upcoming(ctx(), 101)) == (True, False)
    assert (await ledger.pet_has_visits(ctx(), 102), await ledger.pet_has_upcoming(ctx(), 102)) == (True, True)
    assert await ledger.pet_has_visits(ctx(), 103) is False   # 다른 매장


async def test_고객의_앞으로의_예약과_노쇼():
    visits, ledger = _ledger()
    visits.seed(customer_id=1, status="no_show")
    visits.seed(customer_id=2, starts_at=kst(9, 23, 16), status="in_progress", started_at=kst(9, 23, 16))
    assert (await ledger.customer_has_upcoming(ctx(), 1), await ledger.no_show_count(ctx(), 1)) == (False, 1)
    assert await ledger.customer_has_upcoming(ctx(), 2) is True


async def test_다가오는_예약은_오늘부터_시작_순으로():
    visits, ledger = _ledger()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 20, 10))       # 정리 안 된 지난 예약 — 보이지 않는다
    later = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    today = visits.seed(customer_id=1, pet_id=None, starts_at=kst(9, 23, 10))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 9, 14))
    found = await ledger.upcoming_for_customer(ctx(), 1, limit=2)
    assert [(u.visit_id, u.pet_id) for u in found] == [(today.id, None), (later.id, 101)]


async def test_메모를_비운다():
    visits, ledger = _ledger()
    mine = visits.seed(customer_id=1, memo="010-1234-5678 로 연락")
    other = visits.seed(customer_id=2, memo="남의 메모")
    await ledger.clear_customer_memos(ctx(), 1)
    assert (visits.rows[mine.id].memo, visits.rows[other.id].memo) == (None, "남의 메모")
