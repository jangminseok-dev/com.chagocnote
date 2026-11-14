from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_checks_dto import GetVisitChecksQuery, VisitChecksView


class GetVisitChecksUseCase(ABC):
    @abstractmethod
    async def get_visit_checks(self, query: GetVisitChecksQuery) -> VisitChecksView: ...
