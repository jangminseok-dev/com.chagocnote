from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.update_report_settings_use_case import UpdateReportSettingsUseCase
from visit.app.use_cases.update_report_settings_interactor import UpdateReportSettingsInteractor
from visit.dependencies.visit_wiring import build_report_settings_repository, build_schedule_repository


def get_update_report_settings_use_case(db: DbSession) -> UpdateReportSettingsUseCase:
    return UpdateReportSettingsInteractor(
        schedule=build_schedule_repository(db), settings=build_report_settings_repository(db)
    )
