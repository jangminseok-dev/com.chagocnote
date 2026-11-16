from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.get_consent_document_use_case import GetConsentDocumentUseCase
from customer.app.use_cases.get_consent_document_interactor import GetConsentDocumentInteractor
from customer.dependencies.customer_wiring import (
    build_consent_signature_repository, build_pet_repository, consent_policy,
)
from customer.domain.services.pet_age import seoul_today


def get_get_consent_document_use_case(db: DbSession) -> GetConsentDocumentUseCase:
    return GetConsentDocumentInteractor(
        pets=build_pet_repository(db), signatures=build_consent_signature_repository(db), today=seoul_today,
        policy=consent_policy(),
    )
