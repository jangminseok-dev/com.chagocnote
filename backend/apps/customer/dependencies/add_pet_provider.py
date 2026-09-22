from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.add_pet_use_case import AddPetUseCase
from customer.app.use_cases.add_pet_interactor import AddPetInteractor
from customer.dependencies.customer_wiring import (
    build_condition_type_repository,
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_add_pet_use_case(db: DbSession) -> AddPetUseCase:
    return AddPetInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        condition_types=build_condition_type_repository(db), search=build_customer_search(db),
        today=seoul_today,
    )
