from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.set_report_skip_dto import SetReportSkipCommand


class SetReportSkipUseCase(ABC):
    @abstractmethod
    async def set_report_skip(self, command: SetReportSkipCommand) -> None: ...
