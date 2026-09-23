from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.register_visit_dto import RegisteredVisitsView, RegisterVisitCommand
from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import IN_PROGRESS, RESERVED
from visit.domain.errors import MenuNotAvailableError, VisitInputError
from visit.domain.services.visit_schedule import (
    Occupied,
    check_duration,
    check_same_day,
    check_start,
    day_bounds,
    floor_to_step,
    local_date,
    warnings_for,
)
from visit.domain.value_objects.new_visit import NewVisit


class RegisterVisitInteractor(RegisterVisitUseCase):
    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
        directory: CustomerDirectoryPort, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._now = now

    async def register_visit(self, command: RegisterVisitCommand) -> RegisteredVisitsView:
        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
        if command.walk_in == (command.starts_at is not None):
            raise VisitInputError("예약 시각과 '지금 시작' 중 하나만 보내 주세요.")
        settings = await self._schedule.ensure(ctx)
        menus = await self._menus.list_active_by_ids(ctx, list(command.menu_ids))
        if len(menus) != len(command.menu_ids):
            raise MenuNotAvailableError("고를 수 없는 메뉴가 있습니다.")
        duration = command.duration_minutes
        if duration is None:
            duration = sum(m.default_duration_minutes or settings.default_duration_minutes for m in menus) or (
                settings.default_duration_minutes
            )
        check_duration(duration)
        if command.walk_in:
            starts_at, status, started_at = floor_to_step(now, tz), IN_PROGRESS, now
        else:
            starts_at, status, started_at = command.starts_at, RESERVED, None
            check_start(starts_at, now, tz)
        check_same_day(starts_at, duration, tz)

        # 고객 행 → 방문 행. 익명화·무지개다리·반려동물 삭제와 겹치지 않게 가족부터 잠근다(설계 4.2, V3).
        await self._directory.lock_family(ctx, command.customer_id, command.pet_ids)
        created = await self._visits.create_many(
            ctx,
            [
                NewVisit(customer_id=command.customer_id, pet_id=pet_id, starts_at=starts_at,
                         duration_minutes=duration, status=status, started_at=started_at,
                         menu_ids=command.menu_ids, memo=command.memo, created_by_member_id=ctx.member_id)
                for pet_id in (command.pet_ids or (None,))
            ],
        )

        day = local_date(starts_at, tz)
        start, end = day_bounds(day, tz)
        occupied = [Occupied(v.starts_at, v.ends_at, v.group_key)
                    for v in await self._visits.list_occupied(ctx, start, end)]
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
        warnings = warnings_for(starts_at, duration, (command.customer_id, starts_at), tz, settings, closed,
                                occupied)
        return RegisteredVisitsView(
            visits=await describe_visits(ctx, created, self._directory, self._menus), warnings=warnings
        )
