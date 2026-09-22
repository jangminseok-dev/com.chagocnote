from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_get_customer_use_case(db: DbSession) -> GetCustomerUseCase:
    return GetCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
    )
