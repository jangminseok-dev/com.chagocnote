from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.get_pet_use_case import GetPetUseCase
from customer.app.use_cases.get_pet_interactor import GetPetInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_get_pet_use_case(db: DbSession) -> GetPetUseCase:
    return GetPetInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
    )
