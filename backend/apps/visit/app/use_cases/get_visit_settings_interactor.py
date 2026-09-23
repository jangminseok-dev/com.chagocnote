from __future__ import annotations

from visit.app.dtos.get_visit_settings_dto import GetVisitSettingsQuery
from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.app.ports.input.get_visit_settings_use_case import GetVisitSettingsUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository


class GetVisitSettingsInteractor(GetVisitSettingsUseCase):
    """처음 부르는 매장이면 기본 설정과 기본 메뉴가 이때 생긴다."""

    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def get_visit_settings(self, query: GetVisitSettingsQuery) -> VisitSettingsView:
        return VisitSettingsView.of(await self._schedule.ensure(query.ctx))
