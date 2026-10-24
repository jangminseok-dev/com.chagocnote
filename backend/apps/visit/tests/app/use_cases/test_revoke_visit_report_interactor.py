from datetime import timedelta

import pytest

from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
from visit.domain.errors import ReportNotFoundError, VisitNotFoundError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeEvents, FakeReportRepository, FakeVisits, Journal

NOW = kst(9, 24, 10)


class _World:
    def __init__(self) -> None:
        self.journal = Journal()
        self.visits = FakeVisits(self.journal)
        self.reports = FakeReportRepository(self.visits, self.journal)
        directory = FakeDirectory(self.journal)
        directory.family(1, pets=(101,))
        self.events = FakeEvents(self.journal)
        self.interactor = RevokeVisitReportInteractor(self.visits, self.reports, directory, events=self.events,
                                                      now=lambda: NOW)

    async def sent(self, expires_at=None, **fields) -> int:
        """어제 보낸 링크가 달린 완료 방문."""
        found = self.visits.seed(status="completed", started_at=kst(9, 23, 14), **fields)
        await self.reports.create(ctx(shop_id=found.shop_id), found.id, bytes(16), expires_at, NOW - timedelta(days=1))
        self.journal.clear()
        return found.id

    async def revoke(self, visit_id, shop_id=1):
        await self.interactor.revoke_visit_report(RevokeVisitReportCommand(ctx=ctx(shop_id=shop_id), visit_id=visit_id))


async def test_잠근_뒤_살아_있는_링크를_끊는다():
    w = _World()
    visit_id = await w.sent(expires_at=NOW + timedelta(days=6))
    await w.revoke(visit_id)
    assert [r.revoked_at for r in w.reports.rows] == [NOW]
    assert await w.reports.get_live(ctx(), visit_id, NOW) is None
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "revoke_report", "publish"]
    assert [(type(e).__name__, e.visit_id) for e in w.events.published] == [("VisitReportRevoked", visit_id)]


async def test_보낸_적이_없거나_이미_끊었으면_REPORT_NOT_FOUND_다():
    w = _World()
    with pytest.raises(ReportNotFoundError):
        await w.revoke(w.visits.seed(status="completed", started_at=kst(9, 23, 14)).id)
    visit_id = await w.sent()
    await w.revoke(visit_id)
    with pytest.raises(ReportNotFoundError):
        await w.revoke(visit_id)
    assert len(w.events.published) == 1   # 끊지 못하면 발행하지 않는다


async def test_기간이_지난_링크는_끊을_것이_없다():
    w = _World()
    visit_id = await w.sent(expires_at=NOW)   # 지금 끝난다
    with pytest.raises(ReportNotFoundError):
        await w.revoke(visit_id)
    assert [r.revoked_at for r in w.reports.rows] == [None]


async def test_없는_방문과_다른_매장의_방문은_끊을_수_없다():
    """R2"""
    w = _World()
    theirs = await w.sent(shop_id=2)
    for visit_id in (theirs, 999):
        with pytest.raises(VisitNotFoundError):
            await w.revoke(visit_id, shop_id=1)
    assert (w.journal, [r.revoked_at for r in w.reports.rows]) == ([], [None])
