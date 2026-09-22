from __future__ import annotations

from customer.app.dtos.list_pet_condition_types_dto import (
    ConditionTypeView,
    ListPetConditionTypesQuery,
)
from customer.app.ports.input.list_pet_condition_types_use_case import ListPetConditionTypesUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository


class ListPetConditionTypesInteractor(ListPetConditionTypesUseCase):
    def __init__(self, condition_types: ConditionTypeRepository) -> None:
        self._condition_types = condition_types

    async def list_pet_condition_types(
        self, query: ListPetConditionTypesQuery
    ) -> list[ConditionTypeView]:
        return [
            ConditionTypeView(code=t.code, label=t.label, sort_order=t.sort_order)
            for t in await self._condition_types.list_all()
        ]
