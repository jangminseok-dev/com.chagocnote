from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_calendar_dto import GetVisitCalendarQuery, VisitCalendarView


class GetVisitCalendarUseCase(ABC):
    @abstractmethod
    async def get_visit_calendar(self, query: GetVisitCalendarQuery) -> VisitCalendarView: ...
