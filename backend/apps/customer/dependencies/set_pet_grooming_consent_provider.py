from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.set_pet_grooming_consent_use_case import SetPetGroomingConsentUseCase
from customer.app.use_cases.set_pet_grooming_consent_interactor import SetPetGroomingConsentInteractor
from customer.dependencies.customer_wiring import build_customer_repository, build_pet_repository
from customer.domain.services.pet_age import seoul_today


def get_set_pet_grooming_consent_use_case(db: DbSession) -> SetPetGroomingConsentUseCase:
    return SetPetGroomingConsentInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
    )
