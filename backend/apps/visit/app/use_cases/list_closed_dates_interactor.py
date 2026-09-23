from __future__ import annotations

from visit.app.dtos.list_closed_dates_dto import ListClosedDatesQuery
from visit.app.dtos.schedule_view_dto import ClosedDateView
from visit.app.ports.input.list_closed_dates_use_case import ListClosedDatesUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.errors import VisitInputError

MAX_RANGE_DAYS = 400


class ListClosedDatesInteractor(ListClosedDatesUseCase):
    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def list_closed_dates(self, query: ListClosedDatesQuery) -> list[ClosedDateView]:
        if query.start > query.end or (query.end - query.start).days > MAX_RANGE_DAYS:
            raise VisitInputError("기간은 시작이 끝보다 앞서고 400일을 넘지 않아야 합니다.")
        found = await self._schedule.list_closed_dates(query.ctx, query.start, query.end)
        return [ClosedDateView.of(closed) for closed in found]
