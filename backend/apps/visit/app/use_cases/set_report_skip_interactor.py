from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.set_report_skip_dto import SetReportSkipCommand
from visit.app.ports.input.set_report_skip_use_case import SetReportSkipUseCase
from visit.app.ports.output.visit_record_repository import VisitRecordRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.app.services.visit_locking import lock_visits
from visit.domain.entities.visit import COMPLETED
from visit.domain.errors import VisitStateConflictError


class SetReportSkipInteractor(SetReportSkipUseCase):
    """알림장을 보내지 않기로 한다(⑬) — 남은 일 '알림장 안 보냄'에서 빠진다. 완료하고 기록이 있는 방문만이다(남은 일이
    될 수 있는 방문). 되돌리기는 언제나 된다. 잠금은 고객 행 → 방문 행(지금 규칙 그대로)."""

    def __init__(
        self, visits: VisitWriteRepository, records: VisitRecordRepository, directory: CustomerDirectoryPort,
        now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._records = records
        self._directory = directory
        self._now = now

    async def set_report_skip(self, command: SetReportSkipCommand) -> None:
        ctx = command.ctx
        [visit] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory)
        if not command.skip:
            await self._visits.set_report_skipped(ctx, visit.id, None)
            return
        if visit.status != COMPLETED or visit.id not in await self._records.list_many(ctx, [visit.id]):
            raise VisitStateConflictError("완료하고 기록이 있는 방문만 알림장을 보내지 않음으로 넘길 수 있습니다.")
        await self._visits.set_report_skipped(ctx, visit.id, self._now())
