from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.get_visit_report_dto import GetVisitReportQuery, VisitReportPreview
from visit.app.ports.input.get_visit_report_use_case import GetVisitReportUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.report_reader import describe_link, describe_report
from visit.domain.errors import VisitNoRecordYetError


class GetVisitReportInteractor(GetVisitReportUseCase):
    """알림장 미리보기 — 보호자가 볼 내용과 링크의 상태. 읽기만 하므로 잠그지 않는다.
    보내기 전에 보는 화면이라 완료하지 않은 방문도 기록이 있으면 준다."""

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, settings: ReportSettingsRepository,
        reports: ReportRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        library: MediaLibraryPort, shops: ShopProfilePort, now: Callable[[], datetime], link_key: bytes,
        web_base_url: str,
    ) -> None:
        self._visits = visits
        self._records = records
        self._settings = settings
        self._reports = reports
        self._menus = menus
        self._directory = directory
        self._library = library
        self._shops = shops
        self._now = now
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def get_visit_report(self, query: GetVisitReportQuery) -> VisitReportPreview:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        record = await self._records.get(ctx, visit.id)
        if record is None:
            raise VisitNoRecordYetError("기록을 먼저 남겨 주세요.")
        report = await describe_report(
            ctx, visit, record, await self._settings.get(ctx), await self._shops.public_profile(ctx.shop_id),
            self._menus, self._directory, self._library, include_hidden=True,
        )
        live = await self._reports.get_live(ctx, visit.id, self._now())
        link = describe_link(live, self._link_key, self._web_base_url)
        return VisitReportPreview(report=report, link=link.in_zone(ZoneInfo(ctx.timezone)))
