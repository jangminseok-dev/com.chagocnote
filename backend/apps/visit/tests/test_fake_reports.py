"""알림장 링크 스텁이 pg 구현과 같은 규칙을 지키는지 — 뒤 작업의 인터랙터 테스트가 이 스텁에 기댄다."""
from datetime import timedelta

import pytest

from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeReportRepository, FakeVisits

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOW = kst(9, 28, 15)
WEEK = NOW + timedelta(days=7)
FIRST, SECOND = b"\x01" * 16, b"\x02" * 16


def _reports(**visit_fields):
    visits = FakeVisits()
    return FakeReportRepository(visits), visits.seed(**visit_fields)


async def test_만든_링크는_그_매장에서만_살아_있다():
    reports, visit = _reports()
    created = await reports.create(A, visit.id, FIRST, WEEK, NOW)
    assert (created.created_by_member_id, created.created_at) == (11, NOW)
    assert await reports.get_live(A, visit.id, NOW) == created
    assert await reports.live_visit_ids(A, [visit.id, 99], NOW) == {visit.id}
    assert await reports.get_live(A, visit.id, WEEK) is None
    assert await reports.get_live(B, visit.id, NOW) is None
    assert await reports.revoke(B, visit.id, NOW) is False
    found = await reports.find(FIRST)
    assert (found.report, found.shop_id, found.visit) == (created, 1, visit)
    assert await reports.find(SECOND) is None


async def test_끊지_않은_줄이_있는데_또_만들면_테스트_실수다():
    reports, visit = _reports()
    await reports.create(A, visit.id, FIRST, WEEK, NOW)
    with pytest.raises(AssertionError):
        await reports.create(A, visit.id, SECOND, None, WEEK)
    await reports.close_expired(A, visit.id, WEEK)
    assert (await reports.create(A, visit.id, SECOND, None, WEEK)).public_id == SECOND
    assert (await reports.find(FIRST)).report.revoked_at == WEEK


async def test_끊기는_살아_있는_것만_익명화는_그_보호자의_끊지_않은_것_모두():
    reports, visit = _reports()
    theirs = reports.visits.seed(customer_id=2)
    await reports.create(A, visit.id, FIRST, NOW + timedelta(hours=1), NOW)
    await reports.create(A, theirs.id, SECOND, None, NOW)
    assert await reports.revoke(A, visit.id, WEEK) is False   # 기간이 지났다
    await reports.revoke_for_customer(A, 1, WEEK)
    assert [(await reports.find(p)).report.revoked_at for p in (FIRST, SECOND)] == [WEEK, None]
    assert await reports.revoke(A, theirs.id, NOW) is True
    assert await reports.revoke(A, theirs.id, NOW) is False


async def test_처음_연_시각은_한_번만_적는다():
    reports, visit = _reports()
    created = await reports.create(A, visit.id, FIRST, WEEK, NOW)
    await reports.mark_viewed(created.id, NOW)
    await reports.mark_viewed(created.id, WEEK)
    assert (await reports.find(FIRST)).report.first_viewed_at == NOW
