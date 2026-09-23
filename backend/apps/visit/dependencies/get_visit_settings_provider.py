from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_visit_settings_use_case import GetVisitSettingsUseCase
from visit.app.use_cases.get_visit_settings_interactor import GetVisitSettingsInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_get_visit_settings_use_case(db: DbSession) -> GetVisitSettingsUseCase:
    return GetVisitSettingsInteractor(schedule=build_schedule_repository(db))
