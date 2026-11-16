from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.get_form_settings_use_case import GetFormSettingsUseCase
from customer.app.use_cases.get_form_settings_interactor import GetFormSettingsInteractor
from customer.dependencies.customer_wiring import build_form_settings_repository


def get_get_form_settings_use_case(db: DbSession) -> GetFormSettingsUseCase:
    return GetFormSettingsInteractor(settings=build_form_settings_repository(db))
