from __future__ import annotations

from dataclasses import replace

from customer.app.dtos.update_form_settings_dto import UpdateFormSettingsCommand
from customer.app.ports.input.update_form_settings_use_case import UpdateFormSettingsUseCase
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.domain.services.form_settings_rules import check_form_settings
from customer.domain.value_objects.form_settings import FormSettings


class UpdateFormSettingsInteractor(UpdateFormSettingsUseCase):
    """서류 설정을 바꾼다. 이미 낸 링크의 기간과 이미 받은 동의의 받은 날은 그대로다 — 바뀐 값은 그 뒤의 판정부터 쓴다."""

    def __init__(self, settings: FormSettingsRepository) -> None:
        self._settings = settings

    async def update_form_settings(self, command: UpdateFormSettingsCommand) -> FormSettings:
        settings = command.settings
        if command.kept:
            current = await self._settings.get(command.ctx)
            settings = replace(settings, **{name: getattr(current, name) for name in command.kept})
        check_form_settings(settings)
        return await self._settings.put(command.ctx, settings)
