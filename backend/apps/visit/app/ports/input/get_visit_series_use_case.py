from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_series_dto import GetVisitSeriesQuery, VisitSeriesView


class GetVisitSeriesUseCase(ABC):
    @abstractmethod
    async def get_visit_series(self, query: GetVisitSeriesQuery) -> VisitSeriesView: ...
