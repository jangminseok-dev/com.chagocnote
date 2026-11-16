import pytest

from visit.app.dtos.set_report_skip_dto import SetReportSkipCommand
from visit.app.use_cases.set_report_skip_interactor import SetReportSkipInteractor
from visit.domain.errors import VisitNotFoundError, VisitStateConflictError
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeDirectory, FakeRecords, FakeVisits, Journal

NOW = kst(11, 17, 19)


class _World:
    def __init__(self) -> None:
        self.journal = Journal()
        self.visits = FakeVisits(self.journal)
        self.records = FakeRecords(self.visits, self.journal)
        directory = FakeDirectory(self.journal)
        directory.family(1, pets=(101,))
        self.interactor = SetReportSkipInteractor(self.visits, self.records, directory, now=lambda: NOW)

    def done(self, *, with_record=True, **fields) -> int:
        found = self.visits.seed(status="completed", started_at=kst(11, 17, 14), completed_at=kst(11, 17, 16),
                                 **fields)
        if with_record:
            self.records.seed(record(found.id))
        self.journal.clear()
        return found.id

    async def skip(self, visit_id, skip=True, shop_id=1):
        await self.interactor.set_report_skip(
            SetReportSkipCommand(ctx=ctx(shop_id=shop_id), visit_id=visit_id, skip=skip))


async def test_잠근_뒤_보내지_않음을_적고_되돌리면_지운다():
    w = _World()
    visit_id = w.done()
    await w.skip(visit_id)
    assert w.visits.rows[visit_id].report_skipped_at == NOW
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "set_report_skipped"]
    await w.skip(visit_id, skip=False)
    assert w.visits.rows[visit_id].report_skipped_at is None


async def test_완료가_아니거나_기록이_없으면_409이고_되돌리기는_언제나_된다():
    w = _World()
    reserved = w.visits.seed(starts_at=kst(11, 18, 14)).id
    bare = w.done(with_record=False)
    for visit_id in (reserved, bare):
        with pytest.raises(VisitStateConflictError):
            await w.skip(visit_id)
        await w.skip(visit_id, skip=False)
        assert w.visits.rows[visit_id].report_skipped_at is None


async def test_다른_매장의_방문은_없는_방문이다():
    w = _World()
    theirs = w.done(shop_id=2, customer_id=9)
    with pytest.raises(VisitNotFoundError):
        await w.skip(theirs)
