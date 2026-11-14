from datetime import timedelta

import pytest

from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
from visit.domain.entities.visit_record import RecordMedia, VisitRecord
from visit.domain.errors import RecordNotFoundError, VisitReportSentError
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeEvents,
    FakeLibrary,
    FakeRecords,
    FakeReportRepository,
    FakeVisits,
    Journal,
)

NOW = kst(9, 24, 10)
EVENTS = FakeEvents()   # 검색 이벤트만 본다 — 테스트마다 changed 를 비운다


@pytest.fixture(autouse=True)
def _clear_events():
    EVENTS.changed.clear()


def _with_reports(status="completed"):
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101,))
    records, library = FakeRecords(visits, journal), FakeLibrary(journal)
    reports = FakeReportRepository(visits, journal)
    visit = visits.seed(status=status, started_at=kst(9, 23, 14), completed_at=kst(9, 23, 16))
    interactor = DeleteVisitRecordInteractor(visits, records, reports, directory, library, now=lambda: NOW,
                                             events=EVENTS)
    return journal, visit, records, reports, interactor


def _world(status="completed"):
    journal, visit, records, _, interactor = _with_reports(status)
    return journal, visit, records, interactor


async def test_잠근_뒤_미디어를_놓고_기록을_지운다():
    journal, visit, records, interactor = _world()
    records.seed(VisitRecord(visit_id=visit.id, weight_kg=None, care_note=None, internal_note=None,
                             payment_method=None, total_amount=None, items=(),
                             media=(RecordMedia(51, "photo", "after", 0), RecordMedia(52, "video", "before", 0)),
                             version=2, created_by_member_id=11, updated_by_member_id=11))
    await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
    assert visit.id not in records.rows
    assert journal == [("lock_family", 1, ()), ("lock_visits", [visit.id]), ("release", [51, 52]),
                       ("delete_record", visit.id)]


async def test_기록이_없으면_RECORD_NOT_FOUND():
    journal, visit, _, interactor = _world()
    with pytest.raises(RecordNotFoundError):
        await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))


async def _sent(records, reports, visit, expires_at=NOW + timedelta(days=7)):
    """사진 하나가 붙은 기록과 어제 보낸 링크."""
    records.seed(record(visit.id, media=((51, "photo", "after", 0),)))
    await reports.create(ctx(), visit.id, bytes(16), expires_at, NOW - timedelta(days=1))


async def test_알림장을_보낸_방문의_기록은_지울_수_없고_미디어도_놓지_않는다():
    journal, visit, records, reports, interactor = _with_reports()
    await _sent(records, reports, visit)
    journal.clear()
    with pytest.raises(VisitReportSentError):
        await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
    assert visit.id in records.rows
    assert journal == [("lock_family", 1, ()), ("lock_visits", [visit.id])]


async def test_링크를_끊으면_기록을_지울_수_있다():
    _, visit, records, reports, interactor = _with_reports()
    await _sent(records, reports, visit)
    await reports.revoke(ctx(), visit.id, NOW)
    await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
    assert visit.id not in records.rows


async def test_링크의_기간이_지나면_기록을_지울_수_있다():
    _, visit, records, reports, interactor = _with_reports()
    await _sent(records, reports, visit, expires_at=NOW)   # 지금 끝난다
    await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
    assert visit.id not in records.rows


async def test_지우면_그_방문을_다시_색인하라고_알린다():
    _, visit, records, interactor = _world()
    records.seed(record(visit.id, care_note="얌전했어요"))
    await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
    assert EVENTS.changed == [("visit", visit.id)]


async def test_지우지_못하면_알리지_않는다():
    _, visit, _, interactor = _world()
    with pytest.raises(RecordNotFoundError):
        await interactor.delete_visit_record(DeleteVisitRecordCommand(ctx=ctx(), visit_id=visit.id))
    assert EVENTS.changed == []
