from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_day_visits_dto import DayVisitsView, ListDayVisitsQuery


class ListDayVisitsUseCase(ABC):
    @abstractmethod
    async def list_day_visits(self, query: ListDayVisitsQuery) -> DayVisitsView: ...
