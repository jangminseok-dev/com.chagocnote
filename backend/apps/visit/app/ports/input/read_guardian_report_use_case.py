from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.guardian_report_dto import ReadGuardianReportQuery
from visit.app.dtos.read_public_report_dto import PublicReportView


class ReadGuardianReportUseCase(ABC):
    @abstractmethod
    async def read_report(self, query: ReadGuardianReportQuery) -> PublicReportView: ...
