from __future__ import annotations

from guardian.app.dtos.family_dto import GetGuardianSettingsQuery, GuardianSettingsView
from guardian.app.ports.input.get_guardian_settings_use_case import GetGuardianSettingsUseCase
from guardian.app.ports.output.guardian_settings_repository import GuardianSettingsRepository
from guardian.domain.services.family_rules import FAMILY_MAX_DEFAULT


class GetGuardianSettingsInteractor(GetGuardianSettingsUseCase):
    """매장이 정한 가족 수. 정한 적이 없으면 기본값이다(행을 만들지 않는다)."""

    def __init__(self, settings: GuardianSettingsRepository) -> None:
        self._settings = settings

    async def get_settings(self, command: GetGuardianSettingsQuery) -> GuardianSettingsView:
        return GuardianSettingsView(
            family_max=await self._settings.family_max(command.ctx.shop_id), default_family_max=FAMILY_MAX_DEFAULT)
