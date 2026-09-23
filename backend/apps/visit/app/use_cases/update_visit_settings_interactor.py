from __future__ import annotations

from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.app.dtos.update_visit_settings_dto import UpdateVisitSettingsCommand
from visit.app.ports.input.update_visit_settings_use_case import UpdateVisitSettingsUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.services.visit_schedule import check_settings


class UpdateVisitSettingsInteractor(UpdateVisitSettingsUseCase):
    """영업시간·기본 소요·쉬는 요일을 바꾼다. 이미 잡힌 예약은 그대로다(경고만 달라진다)."""

    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def update_visit_settings(self, command: UpdateVisitSettingsCommand) -> VisitSettingsView:
        check_settings(command.settings)
        await self._schedule.ensure(command.ctx)
        return VisitSettingsView.of(await self._schedule.update(command.ctx, command.settings))
