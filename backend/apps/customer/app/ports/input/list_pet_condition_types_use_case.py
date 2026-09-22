from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.list_pet_condition_types_dto import (
    ConditionTypeView,
    ListPetConditionTypesQuery,
)


class ListPetConditionTypesUseCase(ABC):
    @abstractmethod
    async def list_pet_condition_types(
        self, query: ListPetConditionTypesQuery
    ) -> list[ConditionTypeView]: ...
