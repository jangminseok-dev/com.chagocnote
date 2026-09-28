from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_report_settings_dto import GetReportSettingsQuery
from visit.domain.value_objects.report_settings import ReportSettings


class GetReportSettingsUseCase(ABC):
    @abstractmethod
    async def get_report_settings(self, query: GetReportSettingsQuery) -> ReportSettings: ...
