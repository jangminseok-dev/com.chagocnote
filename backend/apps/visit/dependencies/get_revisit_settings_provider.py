from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_revisit_settings_use_case import GetRevisitSettingsUseCase
from visit.app.use_cases.get_revisit_settings_interactor import GetRevisitSettingsInteractor
from visit.dependencies.visit_wiring import build_revisit_settings_repository


def get_get_revisit_settings_use_case(db: DbSession) -> GetRevisitSettingsUseCase:
    return GetRevisitSettingsInteractor(settings=build_revisit_settings_repository(db))
