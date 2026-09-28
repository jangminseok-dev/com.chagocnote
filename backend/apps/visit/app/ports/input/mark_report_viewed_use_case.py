from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.mark_report_viewed_dto import MarkReportViewedCommand


class MarkReportViewedUseCase(ABC):
    @abstractmethod
    async def mark_report_viewed(self, command: MarkReportViewedCommand) -> None: ...
