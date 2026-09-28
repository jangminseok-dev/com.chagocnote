from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.read_public_report_dto import PublicReportView, ReadPublicReportQuery


class ReadPublicReportUseCase(ABC):
    @abstractmethod
    async def read_public_report(self, query: ReadPublicReportQuery) -> PublicReportView: ...
