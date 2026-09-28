from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_report_dto import GetVisitReportQuery, VisitReportPreview


class GetVisitReportUseCase(ABC):
    @abstractmethod
    async def get_visit_report(self, query: GetVisitReportQuery) -> VisitReportPreview: ...
