from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_report_dto import VisitReportPreview
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand


class SendVisitReportUseCase(ABC):
    @abstractmethod
    async def send_visit_report(self, command: SendVisitReportCommand) -> VisitReportPreview: ...
