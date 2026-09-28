from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.update_report_settings_dto import UpdateReportSettingsCommand
from visit.domain.value_objects.report_settings import ReportSettings


class UpdateReportSettingsUseCase(ABC):
    @abstractmethod
    async def update_report_settings(self, command: UpdateReportSettingsCommand) -> ReportSettings: ...
