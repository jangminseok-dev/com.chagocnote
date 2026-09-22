from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.update_customer_use_case import UpdateCustomerUseCase
from customer.app.use_cases.update_customer_interactor import UpdateCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_update_customer_use_case(db: DbSession) -> UpdateCustomerUseCase:
    return UpdateCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today,
    )
