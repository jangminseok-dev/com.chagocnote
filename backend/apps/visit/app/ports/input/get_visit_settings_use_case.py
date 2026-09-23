from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_settings_dto import GetVisitSettingsQuery
from visit.app.dtos.schedule_view_dto import VisitSettingsView


class GetVisitSettingsUseCase(ABC):
    @abstractmethod
    async def get_visit_settings(self, query: GetVisitSettingsQuery) -> VisitSettingsView: ...
