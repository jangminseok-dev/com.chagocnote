from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.visit_events import VisitReportRevoked
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.ports.input.revoke_visit_report_use_case import RevokeVisitReportUseCase
from visit.app.ports.output.report_repository import ReportRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.services.visit_locking import lock_visits
from visit.domain.errors import ReportNotFoundError


class RevokeVisitReportInteractor(RevokeVisitReportUseCase):
    """알림장 링크 끊기 — 살아 있는 링크만 끊는다. 뺀 사진 표시는 그대로 둔다(다시 보낼 때 앱이 그대로 보여 준다).
    잠금은 보내기와 같다(고객 행 → 방문 행). 끊은 뒤 알린다 — 아직 안 나간 알림장 알림톡이 거둬진다(설계 5.2)."""

    def __init__(
        self, visits: VisitLookupRepository, reports: ReportRepository, directory: CustomerDirectoryPort,
        events: DomainEventPort, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._reports = reports
        self._directory = directory
        self._events = events
        self._now = now

    async def revoke_visit_report(self, command: RevokeVisitReportCommand) -> None:
        ctx, now = command.ctx, self._now()
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        if not await self._reports.revoke(ctx, visit.id, now):
            raise ReportNotFoundError("보낸 알림장이 없습니다.")
        await self._events.publish(VisitReportRevoked(
            ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
            starts_at=visit.starts_at, occurred_at=now,
            family_pet_ids=(visit.pet_id,) if visit.pet_id is not None else ()))
