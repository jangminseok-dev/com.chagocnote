from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_closed_dates_dto import ListClosedDatesQuery
from visit.app.dtos.schedule_view_dto import ClosedDateView


class ListClosedDatesUseCase(ABC):
    @abstractmethod
    async def list_closed_dates(self, query: ListClosedDatesQuery) -> list[ClosedDateView]: ...
