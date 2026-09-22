from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
)


def get_delete_customer_use_case(db: DbSession) -> DeleteCustomerUseCase:
    return DeleteCustomerInteractor(
        customers=build_customer_repository(db), search=build_customer_search(db),
    )
