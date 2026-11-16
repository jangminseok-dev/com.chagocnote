from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.update_form_settings_dto import UpdateFormSettingsCommand
from customer.domain.value_objects.form_settings import FormSettings


class UpdateFormSettingsUseCase(ABC):
    @abstractmethod
    async def update_form_settings(self, command: UpdateFormSettingsCommand) -> FormSettings: ...
