from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.search_events import SearchSourceChanged
from hub.app.dtos.visit_events import VisitRescheduled
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView, RescheduleVisitsCommand
from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.entities.visit import RESERVED
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.visit_schedule import check_same_day, check_start


class RescheduleVisitsInteractor(RescheduleVisitsUseCase):
    def __init__(
        self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
        schedule: ScheduleRepository, directory: CustomerDirectoryPort, events: DomainEventPort,
        now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._board = board
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._events = events
        self._now = now

    async def reschedule_visits(self, command: RescheduleVisitsCommand) -> RescheduledVisitsView:
        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
        check_start(command.starts_at, now, tz)
        locked = await lock_visits(ctx, list(command.visit_ids), self._visits, self._directory)
        if any(v.status != RESERVED for v in locked):
            raise VisitStateConflictError("예약됨인 방문만 옮길 수 있습니다.")
        longest = max(v.duration_minutes for v in locked)
        check_same_day(command.starts_at, longest, tz)
        moved = await self._visits.reschedule(ctx, [v.id for v in locked], command.starts_at)
        previous = {v.id: v.starts_at for v in locked}
        family = tuple(sorted(v.pet_id for v in moved if v.pet_id is not None))   # 한 시각으로 옮긴 같은 보호자의 묶음
        for visit in moved:
            await self._events.publish(VisitRescheduled(
                ctx=ctx, visit_id=visit.id, customer_id=visit.customer_id, pet_id=visit.pet_id,
                starts_at=visit.starts_at, occurred_at=now, previous_starts_at=previous[visit.id],
                family_pet_ids=family))
        for visit in moved:   # 검색 문서의 날짜를 새 방문 날로(⑨)
            await self._events.publish(SearchSourceChanged(ctx=ctx, scope="visit", ref_id=visit.id))
        settings = await self._schedule.ensure(ctx)
        warnings = await warnings_after_save(
            ctx, locked[0].customer_id, command.starts_at, longest, settings, self._board, self._schedule
        )
        return RescheduledVisitsView(
            visits=await describe_visits(ctx, moved, self._directory, self._menus), warnings=warnings
        )
