from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
from customer.dependencies.customer_wiring import (
    build_customer_search,
    build_pet_repository,
)


def get_delete_pet_use_case(db: DbSession) -> DeletePetUseCase:
    return DeletePetInteractor(
        pets=build_pet_repository(db), search=build_customer_search(db),
    )
