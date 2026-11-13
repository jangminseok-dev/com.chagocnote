from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.guardian_report_dto import GuardianReportPageView, ListGuardianReportsQuery


class ListGuardianReportsUseCase(ABC):
    @abstractmethod
    async def list_reports(self, query: ListGuardianReportsQuery) -> GuardianReportPageView: ...
