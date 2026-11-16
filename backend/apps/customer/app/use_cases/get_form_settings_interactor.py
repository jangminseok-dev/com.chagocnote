from __future__ import annotations

from customer.app.dtos.get_form_settings_dto import GetFormSettingsQuery
from customer.app.ports.input.get_form_settings_use_case import GetFormSettingsUseCase
from customer.app.ports.output.form_settings_repository import FormSettingsRepository
from customer.domain.value_objects.form_settings import FormSettings


class GetFormSettingsInteractor(GetFormSettingsUseCase):
    """정한 적이 없는 매장은 기본값을 본다. 조회는 설정 행을 만들지 않는다."""

    def __init__(self, settings: FormSettingsRepository) -> None:
        self._settings = settings

    async def get_form_settings(self, query: GetFormSettingsQuery) -> FormSettings:
        return await self._settings.get(query.ctx)
