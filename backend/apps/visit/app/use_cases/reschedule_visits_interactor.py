from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView, RescheduleVisitsCommand
from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.entities.visit import RESERVED
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.visit_schedule import check_same_day, check_start


class RescheduleVisitsInteractor(RescheduleVisitsUseCase):
    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
        directory: CustomerDirectoryPort, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._now = now

    async def reschedule_visits(self, command: RescheduleVisitsCommand) -> RescheduledVisitsView:
        ctx, tz = command.ctx, command.ctx.timezone
        check_start(command.starts_at, self._now(), tz)
        locked = await lock_visits(ctx, list(command.visit_ids), self._visits, self._directory)
        if any(v.status != RESERVED for v in locked):
            raise VisitStateConflictError("예약됨인 방문만 옮길 수 있습니다.")
        longest = max(v.duration_minutes for v in locked)
        check_same_day(command.starts_at, longest, tz)
        moved = await self._visits.reschedule(ctx, [v.id for v in locked], command.starts_at)
        settings = await self._schedule.ensure(ctx)
        warnings = await warnings_after_save(
            ctx, locked[0].customer_id, command.starts_at, longest, settings, self._visits, self._schedule
        )
        return RescheduledVisitsView(
            visits=await describe_visits(ctx, moved, self._directory, self._menus), warnings=warnings
        )
