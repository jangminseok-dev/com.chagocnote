from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.visit_events import VisitRescheduled
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from visit.app.dtos.update_visit_dto import UpdatedVisitView, UpdateVisitCommand
from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.entities.visit import RESERVED
from visit.domain.errors import MenuNotAvailableError, VisitStateConflictError
from visit.domain.services.visit_schedule import check_duration, check_same_day, check_start


class UpdateVisitInteractor(UpdateVisitUseCase):
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

    async def update_visit(self, command: UpdateVisitCommand) -> UpdatedVisitView:
        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
        check_duration(command.duration_minutes)
        # 새로 고른 아이만 가족 확인에 넘긴다(같은 보호자의 아이인지, 무지개다리가 아닌지 — V13).
        # 그대로인 아이는 넘기지 않는다 — 완료한 방문의 아이가 나중에 무지개다리를 건넜어도 메모는 고친다.
        before = await self._visits.get(ctx, command.visit_id)
        changed_pet = command.pet_id is not None and command.pet_id != before.pet_id
        new_pet = (command.pet_id,) if changed_pet else ()
        [current] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory, new_pet)
        if current.pet_id != before.pet_id:
            raise VisitStateConflictError("다른 기기가 먼저 방문을 바꿨습니다. 다시 불러와 주세요.")

        moved = command.starts_at != current.starts_at or command.pet_id != current.pet_id
        if moved and current.status != RESERVED:
            raise VisitStateConflictError("날짜·시간·반려동물은 예약됨일 때만 바꿀 수 있습니다.")
        if command.starts_at != current.starts_at:
            check_start(command.starts_at, now, tz)
        check_same_day(command.starts_at, command.duration_minutes, tz)
        # 지금 붙어 있는 메뉴는 보관됐어도 그대로 둘 수 있다(완료한 방문의 메모만 고치는 경우).
        chosen = set(command.menu_ids)
        allowed = {m.id for m in await self._menus.list_active_by_ids(ctx, list(chosen))} | set(current.menu_ids)
        if not chosen <= allowed:
            raise MenuNotAvailableError("고를 수 없는 메뉴가 있습니다.")

        updated = await self._visits.update_details(
            ctx, current.id, command.starts_at, command.pet_id, command.duration_minutes, command.menu_ids,
            command.memo,
        )
        # 시각이 바뀌었을 때만 알린다 — 반려동물·메뉴·메모만 바뀐 것은 보호자에게 알릴 일이 아니다.
        if updated.starts_at != current.starts_at:
            await self._events.publish(VisitRescheduled(
                ctx=ctx, visit_id=updated.id, customer_id=updated.customer_id, pet_id=updated.pet_id,
                starts_at=updated.starts_at, occurred_at=now, previous_starts_at=current.starts_at))
        warnings = []
        if updated.is_active:
            settings = await self._schedule.ensure(ctx)
            warnings = await warnings_after_save(
                ctx, updated.customer_id, updated.starts_at, updated.duration_minutes, settings, self._board,
                self._schedule,
            )
        [view] = await describe_visits(ctx, [updated], self._directory, self._menus)
        return UpdatedVisitView(visit=view, warnings=warnings)
