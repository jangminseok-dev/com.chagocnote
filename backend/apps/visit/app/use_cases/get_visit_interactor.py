from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.check_view_dto import CheckView
from visit.app.dtos.get_visit_dto import GetVisitQuery, PreviousVisitView, VisitDetailView
from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.visit_check_repository import VisitCheckRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.cover_reader import cover_urls
from visit.app.services.record_reader import describe_record
from visit.app.services.report_reader import describe_link
from visit.app.services.visit_checks import CheckTarget, read_checks
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import ACTIVE_STATUSES
from visit.domain.services.visit_schedule import local_date
from visit.domain.services.visit_marks import marks_of


class GetVisitInteractor(GetVisitUseCase):
    def __init__(
        self, visits: VisitLookupRepository, history: VisitHistoryRepository, ledger: VisitLedgerRepository,
        menus: MenuRepository, directory: CustomerDirectoryPort, records: VisitRecordRepository,
        library: MediaLibraryPort, reports: ReportRepository, now: Callable[[], datetime], link_key: bytes,
        web_base_url: str, checks: VisitCheckRepository,
    ) -> None:
        self._visits = visits
        self._history = history
        self._ledger = ledger
        self._menus = menus
        self._directory = directory
        self._records = records
        self._library = library
        self._reports = reports
        self._now = now
        self._link_key = link_key
        self._web_base_url = web_base_url
        self._checks = checks

    async def get_visit(self, query: GetVisitQuery) -> VisitDetailView:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        group = [v for v in await self._history.list_group(ctx, visit.customer_id, visit.starts_at)
                 if v.id != visit.id]
        previous = await self._history.last_completed_before(ctx, visit.customer_id, visit.pet_id, visit.starts_at)
        [view, *group_views] = await describe_visits(ctx, [visit, *group], self._directory, self._menus)
        records = await self._records.list_many(ctx, [visit.id] + ([previous.id] if previous else []))
        record = records.get(visit.id)
        covers = await cover_urls(ctx, records, self._library)
        now = self._now()
        live = await self._reports.get_live(ctx, visit.id, now)
        return VisitDetailView(
            visit=view,
            group=group_views,
            previous_visit=PreviousVisitView(
                visit_id=previous.id, starts_at=previous.starts_at.astimezone(ZoneInfo(ctx.timezone)),
                cover=covers.get(previous.id),
            ) if previous else None,
            no_show_count=await self._ledger.count_no_show(ctx, visit.customer_id),
            record=await describe_record(ctx, record, self._menus, self._library) if record else None,
            cover=covers.get(visit.id),
            report=describe_link(live, self._link_key, self._web_base_url).in_zone(ZoneInfo(ctx.timezone)),
            checks=await self._read_checks(ctx, visit, now),
            marks=marks_of(visit, record, live is not None),
            report_skipped=visit.report_skipped_at is not None,
        )

    async def _read_checks(self, ctx, visit, now: datetime) -> list[CheckView]:
        """확인할 것은 살아 있는 방문(예약됨·미용 중)에만 있다. 자기 자신과 뒤의 방문은 이력으로 세지 않는다."""
        if visit.status not in ACTIVE_STATUSES:
            return []
        target = CheckTarget(
            key=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
            on=local_date(visit.starts_at, ctx.timezone), before=visit.starts_at,
        )
        read = await read_checks(ctx, [target], self._directory, self._checks, local_date(now, ctx.timezone))
        return [CheckView.of(check) for check in read.by_key[visit.id]]
