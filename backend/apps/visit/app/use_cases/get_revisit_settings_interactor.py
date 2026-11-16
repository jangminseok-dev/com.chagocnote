from __future__ import annotations

from visit.app.dtos.get_revisit_settings_dto import GetRevisitSettingsQuery
from visit.app.ports.input.get_revisit_settings_use_case import GetRevisitSettingsUseCase
from visit.app.ports.output.revisit_settings_repository import RevisitSettingsRepository
from visit.domain.value_objects.revisit_settings import RevisitSettings


class GetRevisitSettingsInteractor(GetRevisitSettingsUseCase):
    """정한 적이 없는 매장은 처음 값을 본다. 조회는 설정 행을 만들지 않는다."""

    def __init__(self, settings: RevisitSettingsRepository) -> None:
        self._settings = settings

    async def get_revisit_settings(self, query: GetRevisitSettingsQuery) -> RevisitSettings:
        return await self._settings.get(query.ctx)
