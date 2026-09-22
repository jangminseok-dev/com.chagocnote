from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.list_pet_condition_types_use_case import ListPetConditionTypesUseCase
from customer.app.use_cases.list_pet_condition_types_interactor import ListPetConditionTypesInteractor
from customer.dependencies.customer_wiring import build_condition_type_repository


def get_list_pet_condition_types_use_case(db: DbSession) -> ListPetConditionTypesUseCase:
    return ListPetConditionTypesInteractor(
        condition_types=build_condition_type_repository(db),
    )
