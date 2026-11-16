from __future__ import annotations

from guardian.app.dtos.family_dto import GuardianSettingsView, UpdateGuardianSettingsCommand
from guardian.app.ports.input.update_guardian_settings_use_case import UpdateGuardianSettingsUseCase
from guardian.app.ports.output.guardian_settings_repository import GuardianSettingsRepository
from guardian.domain.services.family_rules import FAMILY_MAX_DEFAULT, check_family_max


class UpdateGuardianSettingsInteractor(UpdateGuardianSettingsUseCase):
    """매장이 가족 수를 정한다(0~10). 줄여도 이미 이은 가족은 끊지 않는다 — 새 초대·잇기만 막힌다."""

    def __init__(self, settings: GuardianSettingsRepository) -> None:
        self._settings = settings

    async def update_settings(self, command: UpdateGuardianSettingsCommand) -> GuardianSettingsView:
        check_family_max(command.family_max)
        saved = await self._settings.put_family_max(command.ctx.shop_id, command.family_max)
        return GuardianSettingsView(family_max=saved, default_family_max=FAMILY_MAX_DEFAULT)
