from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.list_pet_condition_types_schema import (
    ConditionTypeSchema,
)
from customer.app.dtos.list_pet_condition_types_dto import ListPetConditionTypesQuery
from customer.app.ports.input.list_pet_condition_types_use_case import (
    ListPetConditionTypesUseCase,
)
from customer.dependencies.list_pet_condition_types_provider import (
    get_list_pet_condition_types_use_case,
)
from hub.app.dtos.shop_context import ShopContext

list_pet_condition_types_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@list_pet_condition_types_router.get(
    "/{shop_id}/pet-condition-types", response_model=list[ConditionTypeSchema]
)
async def list_pet_condition_types(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListPetConditionTypesUseCase = Depends(get_list_pet_condition_types_use_case),
) -> list[ConditionTypeSchema]:
    views = await use_case.list_pet_condition_types(ListPetConditionTypesQuery(ctx=ctx))
    return [ConditionTypeSchema(code=v.code, label=v.label, sort_order=v.sort_order) for v in views]
