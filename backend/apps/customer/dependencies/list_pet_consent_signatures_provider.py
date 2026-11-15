from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.list_pet_consent_signatures_use_case import ListPetConsentSignaturesUseCase
from customer.app.use_cases.list_pet_consent_signatures_interactor import ListPetConsentSignaturesInteractor
from customer.dependencies.customer_wiring import build_consent_signature_repository, build_pet_repository


def get_list_pet_consent_signatures_use_case(db: DbSession) -> ListPetConsentSignaturesUseCase:
    return ListPetConsentSignaturesInteractor(
        pets=build_pet_repository(db), signatures=build_consent_signature_repository(db))
