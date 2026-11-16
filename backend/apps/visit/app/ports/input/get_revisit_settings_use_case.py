from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_revisit_settings_dto import GetRevisitSettingsQuery
from visit.domain.value_objects.revisit_settings import RevisitSettings


class GetRevisitSettingsUseCase(ABC):
    @abstractmethod
    async def get_revisit_settings(self, query: GetRevisitSettingsQuery) -> RevisitSettings: ...
