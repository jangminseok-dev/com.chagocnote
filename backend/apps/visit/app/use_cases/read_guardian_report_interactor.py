from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.guardian_report_dto import ReadGuardianReportQuery
from visit.app.dtos.read_public_report_dto import PublicReportView
from visit.app.ports.input.read_guardian_report_use_case import ReadGuardianReportUseCase
from visit.app.ports.output.guardian_report_repository import GuardianReportRepository
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.guardian_scope import guardian_scope
from visit.app.services.report_reader import describe_report
from visit.domain.errors import ReportNotFoundError


class ReadGuardianReportInteractor(ReadGuardianReportUseCase):
    """보호자가 지난 알림장 한 장을 읽는다 — **공개 알림장과 같은 조립**(`describe_report`)이라 내부 메모와 매장이
    끈 항목·뺀 사진은 없다. 기간은 없다(로그인한 보호자에게는 링크 기간이 상관없다). 열람 신호를 찍지 않는다 —
    '링크를 열었는가'의 뜻을 지킨다."""

    def __init__(
        self, reports: GuardianReportRepository, records: VisitRecordRepository, settings: ReportSettingsRepository,
        menus: MenuRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort, shops: ShopProfilePort,
    ) -> None:
        self._reports = reports
        self._records = records
        self._settings = settings
        self._menus = menus
        self._directory = directory
        self._library = library
        self._shops = shops

    async def read_report(self, query: ReadGuardianReportQuery) -> PublicReportView:
        scope = await guardian_scope(query.guardian, self._shops)
        if scope is None:
            raise ReportNotFoundError("알림장을 찾을 수 없습니다.")
        ctx, shop = scope
        sent = await self._reports.get_sent(ctx, query.guardian.customer_id, query.report_id)
        record = await self._records.get(ctx, sent.visit.id) if sent is not None else None
        if sent is None or record is None:
            raise ReportNotFoundError("알림장을 찾을 수 없습니다.")
        report = await describe_report(
            ctx, sent.visit, record, await self._settings.get(ctx), shop, self._menus, self._directory,
            self._library, include_hidden=False,
        )
        return PublicReportView(report=report, expires_at=None)
