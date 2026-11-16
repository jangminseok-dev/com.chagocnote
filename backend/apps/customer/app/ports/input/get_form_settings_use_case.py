from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.get_form_settings_dto import GetFormSettingsQuery
from customer.domain.value_objects.form_settings import FormSettings


class GetFormSettingsUseCase(ABC):
    @abstractmethod
    async def get_form_settings(self, query: GetFormSettingsQuery) -> FormSettings: ...
