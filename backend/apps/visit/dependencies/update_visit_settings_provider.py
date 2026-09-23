from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.update_visit_settings_use_case import UpdateVisitSettingsUseCase
from visit.app.use_cases.update_visit_settings_interactor import UpdateVisitSettingsInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_update_visit_settings_use_case(db: DbSession) -> UpdateVisitSettingsUseCase:
    return UpdateVisitSettingsInteractor(schedule=build_schedule_repository(db))
