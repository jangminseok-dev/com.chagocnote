from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.update_revisit_settings_dto import UpdateRevisitSettingsCommand
from visit.domain.value_objects.revisit_settings import RevisitSettings


class UpdateRevisitSettingsUseCase(ABC):
    @abstractmethod
    async def update_revisit_settings(self, command: UpdateRevisitSettingsCommand) -> RevisitSettings: ...
