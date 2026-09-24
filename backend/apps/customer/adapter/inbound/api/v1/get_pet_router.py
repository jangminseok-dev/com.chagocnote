from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetOverviewSchema
from customer.app.dtos.get_pet_dto import GetPetQuery
from customer.app.ports.input.get_pet_use_case import GetPetUseCase
from customer.dependencies.get_pet_provider import get_get_pet_use_case
from hub.app.dtos.shop_context import ShopContext

get_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@get_pet_router.get("/{shop_id}/pets/{pet_id}", response_model=PetOverviewSchema)
async def get_pet(
    pet_id: PetId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetPetUseCase = Depends(get_get_pet_use_case),
) -> PetOverviewSchema:
    return PetOverviewSchema.of_overview(await use_case.get_pet(GetPetQuery(ctx=ctx, pet_id=pet_id)))
