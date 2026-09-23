from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_defaults_dto import GetVisitDefaultsQuery, VisitDefaultsView


class GetVisitDefaultsUseCase(ABC):
    @abstractmethod
    async def get_visit_defaults(self, query: GetVisitDefaultsQuery) -> VisitDefaultsView: ...
