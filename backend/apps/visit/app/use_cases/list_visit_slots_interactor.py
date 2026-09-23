from __future__ import annotations

from zoneinfo import ZoneInfo

from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery, SlotView, VisitSlotsView
from visit.app.ports.input.list_visit_slots_use_case import ListVisitSlotsUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_schedule import (
    STEP_MINUTES,
    Occupied,
    at_local,
    check_duration,
    day_bounds,
    hourly_starts,
    is_closed_day,
    warnings_for,
)


class ListVisitSlotsInteractor(ListVisitSlotsUseCase):
    """예약 ② 화면의 시간 칸. 경고 판단은 서버 한 곳에만 둔다 — 앱은 이 응답만 보고 줄을 긋는다(설계 6.3)."""

    def __init__(self, visits: VisitRepository, schedule: ScheduleRepository) -> None:
        self._visits = visits
        self._schedule = schedule

    async def list_visit_slots(self, query: ListVisitSlotsQuery) -> VisitSlotsView:
        ctx, tz, day = query.ctx, query.ctx.timezone, query.day
        settings = await self._schedule.ensure(ctx)
        duration = query.duration_minutes or settings.default_duration_minutes
        check_duration(duration)
        if query.at is not None and query.at.minute % STEP_MINUTES:
            raise VisitInputError("시각은 10분 단위여야 합니다.")
        start, end = day_bounds(day, tz)
        occupied = [
            Occupied(v.starts_at, v.ends_at, v.group_key)
            for v in await self._visits.list_occupied(ctx, start, end) if v.id not in query.exclude
        ]
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
        starts = [at_local(day, query.at, tz)] if query.at is not None else hourly_starts(day, settings, tz)
        zone = ZoneInfo(tz)
        return VisitSlotsView(
            date=day, duration_minutes=duration, closed_day=is_closed_day(day, settings, closed),
            slots=[
                SlotView(starts_at=s.astimezone(zone),
                         warnings=warnings_for(s, duration, None, tz, settings, closed, occupied))
                for s in starts
            ],
        )
