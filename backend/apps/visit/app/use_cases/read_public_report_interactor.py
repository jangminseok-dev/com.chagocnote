from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.read_public_report_dto import PublicReportView, ReadPublicReportQuery
from visit.app.ports.input.read_public_report_use_case import ReadPublicReportUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.public_report_limiter_port import PublicReportLimiterPort
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.public_context import public_context
from visit.app.services.public_report_gate import open_report
from visit.app.services.report_reader import describe_report
from visit.domain.errors import ReportClosedError


class ReadPublicReportInteractor(ReadPublicReportUseCase):
    """보호자가 링크로 알림장을 읽는다. 로그인이 없다 — 토큰의 서명이 곧 범위다. 읽기만 하므로 잠그지 않는다."""

    def __init__(
        self, reports: PublicReportRepository, records: VisitRecordRepository, settings: ReportSettingsRepository,
        menus: MenuRepository, directory: CustomerDirectoryPort, library: MediaLibraryPort, shops: ShopProfilePort,
        limiter: PublicReportLimiterPort, now: Callable[[], datetime], link_key: bytes,
    ) -> None:
        self._reports = reports
        self._records = records
        self._settings = settings
        self._menus = menus
        self._directory = directory
        self._library = library
        self._shops = shops
        self._limiter = limiter
        self._now = now
        self._link_key = link_key

    async def read_public_report(self, query: ReadPublicReportQuery) -> PublicReportView:
        target, shop = await open_report(
            query.token, query.client, self._now(), link_key=self._link_key, reports=self._reports,
            shops=self._shops, limiter=self._limiter,
        )
        ctx = public_context(shop)
        record = await self._records.get(ctx, target.visit.id)
        if record is None:
            raise ReportClosedError("닫힌 알림장입니다.")
        report = await describe_report(
            ctx, target.visit, record, await self._settings.get(ctx), shop, self._menus, self._directory,
            self._library, include_hidden=False,
        )
        expires_at = target.report.expires_at
        return PublicReportView(
            report=report, expires_at=expires_at.astimezone(ZoneInfo(ctx.timezone)) if expires_at else None)
