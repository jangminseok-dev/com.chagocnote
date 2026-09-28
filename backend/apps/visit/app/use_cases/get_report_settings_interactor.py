from __future__ import annotations

from visit.app.dtos.get_report_settings_dto import GetReportSettingsQuery
from visit.app.ports.input.get_report_settings_use_case import GetReportSettingsUseCase
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.domain.value_objects.report_settings import ReportSettings


class GetReportSettingsInteractor(GetReportSettingsUseCase):
    """정한 적이 없는 매장은 기본값을 본다. 조회는 설정 행을 만들지 않는다."""

    def __init__(self, settings: ReportSettingsRepository) -> None:
        self._settings = settings

    async def get_report_settings(self, query: GetReportSettingsQuery) -> ReportSettings:
        return await self._settings.get(query.ctx)
