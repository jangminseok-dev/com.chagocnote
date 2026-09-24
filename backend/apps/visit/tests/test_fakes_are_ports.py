"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeSchedule,
    FakeVisits,
)


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    assert isinstance(FakeSchedule(), ScheduleRepository)
    assert isinstance(FakeMenus(), MenuRepository)
    assert isinstance(FakeDirectory(), CustomerDirectoryPort)
    assert isinstance(FakeLibrary(), MediaLibraryPort)
    visits = FakeVisits()
    for port in (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
                 VisitBoardRepository):
        assert isinstance(visits, port), port.__name__
    assert isinstance(FakeRecords(visits), VisitRecordRepository)
