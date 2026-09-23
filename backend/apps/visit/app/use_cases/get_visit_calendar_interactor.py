from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime

from visit.app.dtos.get_visit_calendar_dto import (
    CalendarDayView,
    GetVisitCalendarQuery,
    VisitCalendarView,
)
from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import COMPLETED
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_board import COUNTED, is_unresolved
from visit.domain.services.visit_schedule import day_bounds, is_closed_day, local_date


class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
    """월 달력 — 날마다 마릿수·완료·예약·정리 안 됨, 휴무. 위쪽 '정리 안 된 예약 N건'은 매장 전체다."""

    def __init__(
        self, visits: VisitRepository, schedule: ScheduleRepository, now: Callable[[], datetime]
    ) -> None:
        self._visits = visits
        self._schedule = schedule
        self._now = now

    async def get_visit_calendar(self, query: GetVisitCalendarQuery) -> VisitCalendarView:
        ctx, tz = query.ctx, query.ctx.timezone
        if not (1 <= query.month <= 12 and 2000 <= query.year <= 2100):
            raise VisitInputError("달이 올바르지 않습니다.")
        settings = await self._schedule.ensure(ctx)
        last = calendar.monthrange(query.year, query.month)[1]
        first_day, last_day = date(query.year, query.month, 1), date(query.year, query.month, last)
        start, _ = day_bounds(first_day, tz)
        _, end = day_bounds(last_day, tz)
        today = local_date(self._now(), tz)

        by_day = defaultdict(list)
        for visit in await self._visits.list_between(ctx, start, end):
            by_day[local_date(visit.starts_at, tz)].append(visit)
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, first_day, last_day))
        days = []
        for number in range(1, last + 1):
            day = date(query.year, query.month, number)
            visits = by_day[day]
            days.append(CalendarDayView(
                date=day,
                visit_count=sum(v.status in COUNTED for v in visits),
                completed_count=sum(v.status == COMPLETED for v in visits),
                open_count=sum(v.is_active for v in visits),
                unresolved_count=sum(is_unresolved(v, today, tz) for v in visits),
                closed_day=is_closed_day(day, settings, closed),
            ))
        today_start, _ = day_bounds(today, tz)
        total, oldest = await self._visits.unresolved_before(ctx, today_start)
        return VisitCalendarView(
            year=query.year, month=query.month, days=days, unresolved_total=total,
            oldest_unresolved_date=local_date(oldest, tz) if oldest else None,
        )
