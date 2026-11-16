from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.app.dtos.family_dto import GuardianSettingsView, UpdateGuardianSettingsCommand


class UpdateGuardianSettingsUseCase(ABC):
    @abstractmethod
    async def update_settings(self, command: UpdateGuardianSettingsCommand) -> GuardianSettingsView: ...
