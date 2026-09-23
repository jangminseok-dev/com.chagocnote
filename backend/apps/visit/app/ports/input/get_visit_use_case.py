from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_dto import GetVisitQuery, VisitDetailView


class GetVisitUseCase(ABC):
    @abstractmethod
    async def get_visit(self, query: GetVisitQuery) -> VisitDetailView: ...
