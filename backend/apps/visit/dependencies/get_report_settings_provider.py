from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_report_settings_use_case import GetReportSettingsUseCase
from visit.app.use_cases.get_report_settings_interactor import GetReportSettingsInteractor
from visit.dependencies.visit_wiring import build_report_settings_repository


def get_get_report_settings_use_case(db: DbSession) -> GetReportSettingsUseCase:
    return GetReportSettingsInteractor(settings=build_report_settings_repository(db))
