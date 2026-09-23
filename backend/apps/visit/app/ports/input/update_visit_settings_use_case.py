from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.app.dtos.update_visit_settings_dto import UpdateVisitSettingsCommand


class UpdateVisitSettingsUseCase(ABC):
    @abstractmethod
    async def update_visit_settings(self, command: UpdateVisitSettingsCommand) -> VisitSettingsView: ...
