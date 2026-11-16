from __future__ import annotations

from dataclasses import replace

from visit.app.dtos.update_revisit_settings_dto import UpdateRevisitSettingsCommand
from visit.app.ports.input.update_revisit_settings_use_case import UpdateRevisitSettingsUseCase
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.services.revisit_rules import check_revisit_settings
from visit.domain.value_objects.revisit_settings import RevisitSettings


class UpdateRevisitSettingsInteractor(UpdateRevisitSettingsUseCase):
    """보낸 칸만 지금 값 위에 얹어 통째로 저장한다. 목록·초안·하루의 수는 읽을 때 계산하므로 바로 따라온다."""

    def __init__(self, schedule: ScheduleRepository, settings: RevisitSettingsRepository) -> None:
        self._schedule = schedule
        self._settings = settings

    async def update_revisit_settings(self, command: UpdateRevisitSettingsCommand) -> RevisitSettings:
        settings = replace(await self._settings.get(command.ctx), **command.changes)
        check_revisit_settings(settings)
        await self._schedule.ensure(command.ctx)   # 설정 행은 일정 설정과 함께 쓴다 — 없으면 여기서 생긴다
        return await self._settings.update(command.ctx, settings)
