from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.dtos.delete_visit_record_dto import DeleteVisitRecordCommand
from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.services.visit_locking import lock_visits
from visit.domain.errors import RecordNotFoundError, VisitReportSentError


class DeleteVisitRecordInteractor(DeleteVisitRecordUseCase):
    """기록을 지운다 — 방문은 남는다. 붙은 미디어는 놓고, 정리 스크립트가 지운다(설계 8절).
    상태와 상관없이 지울 수 있다(되돌린 방문에 남은 기록도). 알림장을 보낸 방문의 기록은 링크를 끊어야 지울 수 있다."""

    def __init__(
        self, visits: VisitLookupRepository, records: VisitRecordRepository, reports: ReportRepository,
        directory: CustomerDirectoryPort, library: MediaLibraryPort, now: Callable[[], datetime],
        events: DomainEventPort,
    ) -> None:
        self._visits = visits
        self._records = records
        self._reports = reports
        self._directory = directory
        self._library = library
        self._now = now
        self._events = events

    async def delete_visit_record(self, command: DeleteVisitRecordCommand) -> None:
        ctx = command.ctx
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        current = await self._records.get(ctx, visit.id)
        if current is None:
            raise RecordNotFoundError("기록이 없습니다.")
        if await self._reports.get_live(ctx, visit.id, self._now()) is not None:
            raise VisitReportSentError("알림장을 보낸 방문입니다. 링크를 먼저 끊어 주세요.")
        await self._library.release(ctx, [m.media_id for m in current.media])
        await self._records.delete(ctx, visit.id)
        await self._events.publish(SearchSourceChanged(ctx=ctx, scope="visit", ref_id=visit.id))   # 검색에서도 지운다(⑨)
