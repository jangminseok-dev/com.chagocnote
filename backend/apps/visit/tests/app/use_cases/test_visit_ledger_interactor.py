from datetime import timedelta

from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeRecords, FakeReportRepository, FakeVisits

NOW = kst(9, 23, 15)


def _with_reports():
    visits = FakeVisits()
    records, reports = FakeRecords(visits), FakeReportRepository(visits)
    return visits, records, reports, VisitLedgerInteractor(visits, records, reports, now=lambda: NOW)


def _ledger():
    visits, _, _, ledger = _with_reports()
    return visits, ledger


def _with_records():
    visits, records, _, ledger = _with_reports()
    return visits, records, ledger


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


async def test_익명화는_방문_메모와_기록의_두_메모를_비우고_사진은_남긴다():
    visits, records, ledger = _with_records()
    mine = visits.seed(customer_id=1, memo="010-1234-5678 로 연락", status="completed", started_at=kst(9, 2, 10),
                       completed_at=kst(9, 2, 12))
    other = visits.seed(customer_id=2, status="completed", started_at=kst(9, 2, 10), completed_at=kst(9, 2, 12))
    records.seed(record(mine.id, media=((51, "photo", "after", 0),), care_note="보호자 이름", internal_note="번호"))
    records.seed(record(other.id, care_note="남의 기록"))
    await ledger.clear_customer_memos(ctx(), 1)
    kept = records.rows[mine.id]
    assert (visits.rows[mine.id].memo, kept.care_note, kept.internal_note, len(kept.media)) == (None, None, None, 1)
    assert records.rows[other.id].care_note == "남의 기록"


async def test_반려동물마다_사진이_붙은_가장_최근_완료_방문의_대표():
    visits, records, ledger = _with_records()
    done = dict(status="completed", started_at=kst(9, 1, 10), completed_at=kst(9, 1, 12))
    old = visits.seed(pet_id=101, starts_at=kst(9, 1, 10), **done)
    latest = visits.seed(pet_id=101, starts_at=kst(9, 10, 10), **done)
    newest_no_photo = visits.seed(pet_id=101, starts_at=kst(9, 20, 10), **done)
    working = visits.seed(pet_id=101, starts_at=kst(9, 23, 10), status="in_progress", started_at=kst(9, 23, 10))
    only_video = visits.seed(pet_id=102, starts_at=kst(9, 5, 10), **done)
    records.seed(record(old.id, media=((51, "photo", "after", 0),)))
    records.seed(record(latest.id, media=((52, "photo", "before", 0), (53, "photo", "after", 0))))
    records.seed(record(newest_no_photo.id, care_note="사진 없음"))
    records.seed(record(working.id, media=((54, "photo", "after", 0),)))
    records.seed(record(only_video.id, media=((61, "video", "after", 0),)))
    assert await ledger.latest_covers(ctx(), [101, 102, 103]) == {101: 53, 102: 61}


async def test_익명화는_그_보호자의_끊지_않은_링크를_모두_끊고_다른_보호자의_것은_그대로다():
    """R19 — 기간이 지났지만 끊지 않은 줄도 끊는다."""
    visits, _, reports, ledger = _with_reports()
    done = dict(status="completed", started_at=kst(9, 2, 10), completed_at=kst(9, 2, 12))
    live = visits.seed(customer_id=1, starts_at=kst(9, 2, 10), **done)
    expired = visits.seed(customer_id=1, starts_at=kst(9, 9, 10), **done)
    others = visits.seed(customer_id=2, **done)
    theirs = visits.seed(customer_id=1, shop_id=2, **done)   # 다른 매장의 같은 번호 고객
    sent_at = NOW - timedelta(days=8)
    for visit, shop_id, expires_at in ((live, 1, None), (expired, 1, NOW - timedelta(days=1)), (others, 1, None),
                                       (theirs, 2, None)):
        await reports.create(ctx(shop_id=shop_id), visit.id, bytes(16), expires_at, sent_at)
    await ledger.clear_customer_memos(ctx(), 1)
    assert {r.visit_id: r.revoked_at for r in reports.rows} == {
        live.id: NOW, expired.id: NOW, others.id: None, theirs.id: None}
    assert await reports.live_visit_ids(ctx(), [live.id, expired.id, others.id], NOW) == {others.id}
