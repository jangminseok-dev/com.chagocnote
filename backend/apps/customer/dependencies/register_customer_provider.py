from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.register_customer_use_case import RegisterCustomerUseCase
from customer.app.use_cases.register_customer_interactor import RegisterCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_condition_type_repository,
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_register_customer_use_case(db: DbSession) -> RegisterCustomerUseCase:
    return RegisterCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        condition_types=build_condition_type_repository(db), search=build_customer_search(db),
        today=seoul_today,
    )
