from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.update_revisit_settings_use_case import UpdateRevisitSettingsUseCase
from visit.app.use_cases.update_revisit_settings_interactor import UpdateRevisitSettingsInteractor
from visit.dependencies.visit_wiring import build_revisit_settings_repository, build_schedule_repository


def get_update_revisit_settings_use_case(db: DbSession) -> UpdateRevisitSettingsUseCase:
    return UpdateRevisitSettingsInteractor(
        schedule=build_schedule_repository(db), settings=build_revisit_settings_repository(db)
    )
