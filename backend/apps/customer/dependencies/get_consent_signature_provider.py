from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.get_consent_signature_use_case import GetConsentSignatureUseCase
from customer.app.use_cases.get_consent_signature_interactor import GetConsentSignatureInteractor
from customer.dependencies.customer_wiring import build_consent_signature_repository, build_consent_text_repository


def get_get_consent_signature_use_case(db: DbSession) -> GetConsentSignatureUseCase:
    return GetConsentSignatureInteractor(
        signatures=build_consent_signature_repository(db), texts=build_consent_text_repository(db))
