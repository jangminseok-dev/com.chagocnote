from __future__ import annotations

from dataclasses import replace

from visit.app.dtos.update_report_settings_dto import UpdateReportSettingsCommand
from visit.app.ports.input.update_report_settings_use_case import UpdateReportSettingsUseCase
from visit.app.ports.output.report_settings_repository import ReportSettingsRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.services.report_rules import check_settings
from visit.domain.value_objects.report_settings import ReportSettings


class UpdateReportSettingsInteractor(UpdateReportSettingsUseCase):
    """링크 기간과 보여 줄 항목을 바꾼다. 이미 보낸 링크의 기간은 그대로고, 보여 줄 항목은 바로 적용된다."""

    def __init__(self, schedule: ScheduleRepository, settings: ReportSettingsRepository) -> None:
        self._schedule = schedule
        self._settings = settings

    async def update_report_settings(self, command: UpdateReportSettingsCommand) -> ReportSettings:
        settings = command.settings
        if command.kept:
            current = await self._settings.get(command.ctx)
            settings = replace(settings, **{name: getattr(current, name) for name in command.kept})
        check_settings(settings)
        await self._schedule.ensure(command.ctx)   # 설정 행은 일정 설정과 함께 쓴다 — 없으면 여기서 생긴다
        return await self._settings.update(command.ctx, settings)
