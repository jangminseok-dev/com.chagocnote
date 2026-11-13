from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.clear_pet_grooming_consent_use_case import ClearPetGroomingConsentUseCase
from customer.app.use_cases.clear_pet_grooming_consent_interactor import ClearPetGroomingConsentInteractor
from customer.dependencies.customer_wiring import build_customer_repository, build_pet_repository
from customer.domain.services.pet_age import seoul_today


def get_clear_pet_grooming_consent_use_case(db: DbSession) -> ClearPetGroomingConsentUseCase:
    return ClearPetGroomingConsentInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
    )
