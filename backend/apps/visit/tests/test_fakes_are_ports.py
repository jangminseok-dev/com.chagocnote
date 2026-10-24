"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.tests.helpers.builders import ctx
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_feed_repository import VisitFeedRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakePublicReportLimiter,
    FakeRecords,
    FakeReportRepository,
    FakeReportSettingsRepository,
    FakeSchedule,
    FakeShopProfile,
    FakeVisits,
)


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    assert isinstance(FakeSchedule(), ScheduleRepository)
    assert isinstance(FakeMenus(), MenuRepository)
    assert isinstance(FakeDirectory(), CustomerDirectoryPort)
    assert isinstance(FakeLibrary(), MediaLibraryPort)
    assert isinstance(FakeShopProfile(), ShopProfilePort)
    visits = FakeVisits()
    for port in (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
                 VisitBoardRepository, VisitFeedRepository):
        assert isinstance(visits, port), port.__name__
    assert isinstance(FakeRecords(visits), VisitRecordRepository)
    reports = FakeReportRepository(visits)
    assert isinstance(reports, ReportRepository) and isinstance(reports, PublicReportRepository)
    assert isinstance(FakeReportSettingsRepository(), ReportSettingsRepository)
    assert isinstance(FakePublicReportLimiter(), PublicReportLimiterPort)


async def test_매장_공개_정보_스텁은_넣어_둔_매장만_돌려준다():
    profile = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
    shops = FakeShopProfile({1: profile})
    assert (await shops.public_profile(1), await shops.public_profile(2)) == (profile, None)


async def test_고객_연락처_스텁은_넣어_둔_가족의_것만_준다():
    directory = FakeDirectory()
    directory.family(customer_id=1, shop_id=1, name="박서준")
    contact = await directory.contact(ctx(), 1)
    assert (contact.customer_id, contact.name, contact.phone, contact.marketing_consent) == (
        1, "박서준", "01012345678", True,
    )
    assert (await directory.contact(ctx(shop_id=2), 1), await directory.contact(ctx(), 2)) == (None, None)
