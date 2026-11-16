from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.update_form_settings_use_case import UpdateFormSettingsUseCase
from customer.app.use_cases.update_form_settings_interactor import UpdateFormSettingsInteractor
from customer.dependencies.customer_wiring import build_form_settings_repository


def get_update_form_settings_use_case(db: DbSession) -> UpdateFormSettingsUseCase:
    return UpdateFormSettingsInteractor(settings=build_form_settings_repository(db))
