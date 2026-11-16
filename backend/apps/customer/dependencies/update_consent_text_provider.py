from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.update_consent_text_use_case import UpdateConsentTextUseCase
from customer.app.use_cases.update_consent_text_interactor import UpdateConsentTextInteractor
from customer.dependencies.customer_wiring import build_consent_text_repository


def get_update_consent_text_use_case(db: DbSession) -> UpdateConsentTextUseCase:
    return UpdateConsentTextInteractor(texts=build_consent_text_repository(db))
