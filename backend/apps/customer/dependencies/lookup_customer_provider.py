from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.lookup_customer_use_case import LookupCustomerUseCase
from customer.app.use_cases.lookup_customer_interactor import LookupCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_pet_repository,
)


def get_lookup_customer_use_case(db: DbSession) -> LookupCustomerUseCase:
    return LookupCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
    )
