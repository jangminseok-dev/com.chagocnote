from __future__ import annotations

from dataclasses import replace

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.dtos.visit_events import VisitReportIssued
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.dtos.get_visit_report_dto import VisitReportPreview
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.ports.input.send_visit_report_use_case import SendVisitReportUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.report_reader import describe_link, describe_report
from visit.app.services.visit_locking import lock_visits
from visit.domain.services.report_rules import check_not_empty, check_sendable, expires_at_for
from core.link_token import new_public_id


class SendVisitReportInteractor(SendVisitReportUseCase):
    """알림장 보내기 — 뺀 사진을 저장하고, 살아 있는 링크가 없으면 만든다(설계 6.1).

    처음 보내기·다시 공유·보낸 뒤 사진 빼기를 함께 맡는다. 같은 본문으로 다시 불러도 같은 링크다.
    고객 행 → 방문 행을 잠근 뒤에 링크를 읽으므로 동시에 두 번 보내도 링크는 하나다. 기간이 지난 줄은
    먼저 닫아야 새 줄을 만들 수 있다(끊지 않은 줄은 방문에 하나). 검사는 링크·뺀 표시를 쓰기 전에 끝낸다.
    새 링크를 만들었을 때만 알린다 — 알림톡은 링크마다 한 번이다(설계 5.2).
    """

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, settings: ReportSettingsRepository,
        reports: ReportRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        library: MediaLibraryPort, shops: ShopProfilePort, events: DomainEventPort, now: Callable[[], datetime],
        link_key: bytes, web_base_url: str,
    ) -> None:
        self._visits = visits
        self._records = records
        self._settings = settings
        self._reports = reports
        self._menus = menus
        self._directory = directory
        self._library = library
        self._shops = shops
        self._events = events
        self._now = now
        self._link_key = link_key
        self._web_base_url = web_base_url

    async def send_visit_report(self, command: SendVisitReportCommand) -> VisitReportPreview:
        ctx, hidden_ids, now = command.ctx, command.hidden_media_ids, self._now()
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        record = await self._records.get(ctx, visit.id)
        check_sendable(visit, record, hidden_ids)
        settings = await self._settings.get(ctx)

        await self._reports.close_expired(ctx, visit.id, now)
        live = await self._reports.get_live(ctx, visit.id, now)
        issued = live is None
        if issued:
            check_not_empty(record, hidden_ids)
            live = await self._reports.create(
                ctx, visit.id, new_public_id(), expires_at_for(now, settings.link_days), now)
        await self._records.set_hidden(ctx, visit.id, hidden_ids)
        if live.show_review != command.show_review:     # 리뷰 남기기 줄(⑫) — 알림장마다, 다시 보낼 때 바뀐다
            await self._reports.set_show_review(ctx, live.id, command.show_review)
            live = replace(live, show_review=command.show_review)

        report = await describe_report(
            ctx, visit, await self._records.get(ctx, visit.id), settings,
            await self._shops.public_profile(ctx.shop_id), self._menus, self._directory, self._library,
            include_hidden=True,
        )
        link = describe_link(live, self._link_key, self._web_base_url)
        if issued:
            await self._events.publish(VisitReportIssued(
                ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
                starts_at=visit.starts_at, occurred_at=now, url=link.url, expires_at=live.expires_at,
                family_pet_ids=(visit.pet_id,) if visit.pet_id is not None else ()))
        return VisitReportPreview(report=report, link=link.in_zone(ZoneInfo(ctx.timezone)))
