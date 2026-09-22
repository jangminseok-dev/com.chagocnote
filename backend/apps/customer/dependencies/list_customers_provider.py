from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.list_customers_use_case import ListCustomersUseCase
from customer.app.use_cases.list_customers_interactor import ListCustomersInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_list_customers_use_case(db: DbSession) -> ListCustomersUseCase:
    return ListCustomersInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today,
    )
