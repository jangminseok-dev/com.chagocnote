from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.family_dto import GetGuardianSettingsQuery, GuardianSettingsView


class GetGuardianSettingsUseCase(ABC):
    @abstractmethod
    async def get_settings(self, command: GetGuardianSettingsQuery) -> GuardianSettingsView: ...
