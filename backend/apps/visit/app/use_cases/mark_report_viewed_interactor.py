from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.mark_report_viewed_dto import MarkReportViewedCommand
from visit.app.ports.input.mark_report_viewed_use_case import MarkReportViewedUseCase
from hub.app.ports.public_limiter_port import PublicLimiterPort
from visit.app.ports.output.public_report_repository import PublicReportRepository
from visit.app.services.public_report_gate import open_report


class MarkReportViewedInteractor(MarkReportViewedUseCase):
    """보호자가 알림장을 처음 연 시각을 남긴다. 닫힌 링크에는 남기지 않는다(설계 7.5 R11).

    잠그지 않는다 — 저장소의 조건부 UPDATE 한 줄이 처음 한 번만 적는다(R10).
    """

    def __init__(
        self, reports: PublicReportRepository, shops: ShopProfilePort, limiter: PublicLimiterPort,
        now: Callable[[], datetime], link_key: bytes,
    ) -> None:
        self._reports = reports
        self._shops = shops
        self._limiter = limiter
        self._now = now
        self._link_key = link_key

    async def mark_report_viewed(self, command: MarkReportViewedCommand) -> None:
        now = self._now()
        target, _ = await open_report(
            command.token, command.client, now, link_key=self._link_key, reports=self._reports,
            shops=self._shops, limiter=self._limiter,
        )
        await self._reports.mark_viewed(target.report.id, now)
