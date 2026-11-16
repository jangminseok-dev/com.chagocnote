from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_day_wrap_up_dto import DayWrapUpView, GetDayWrapUpQuery


class GetDayWrapUpUseCase(ABC):
    @abstractmethod
    async def get_day_wrap_up(self, query: GetDayWrapUpQuery) -> DayWrapUpView: ...
