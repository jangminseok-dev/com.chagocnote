from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand


class RevokeVisitReportUseCase(ABC):
    @abstractmethod
    async def revoke_visit_report(self, command: RevokeVisitReportCommand) -> None: ...
