import pytest

from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
from visit.domain.entities.visit_record import RecordMedia, VisitRecord
from visit.domain.errors import RecordNotFoundError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeLibrary, FakeRecords, FakeVisits, Journal


def _world(status="completed"):
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101,))
    records, library = FakeRecords(visits, journal), FakeLibrary(journal)
    visit = visits.seed(status=status, started_at=kst(9, 23, 14), completed_at=kst(9, 23, 16))
    return journal, visit, records, DeleteVisitRecordInteractor(visits, records, directory, library)


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
