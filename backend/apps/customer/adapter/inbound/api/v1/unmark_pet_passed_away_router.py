from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.app.dtos.unmark_pet_passed_away_dto import UnmarkPetPassedAwayCommand
from customer.app.ports.input.unmark_pet_passed_away_use_case import UnmarkPetPassedAwayUseCase
from customer.dependencies.unmark_pet_passed_away_provider import (
    get_unmark_pet_passed_away_use_case,
)
from hub.app.dtos.shop_context import ShopContext

unmark_pet_passed_away_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@unmark_pet_passed_away_router.delete(
    "/{shop_id}/pets/{pet_id}/passed-away", response_model=PetDetailSchema
)
async def unmark_pet_passed_away(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: UnmarkPetPassedAwayUseCase = Depends(get_unmark_pet_passed_away_use_case),
) -> PetDetailSchema:
    view = await use_case.unmark_pet_passed_away(UnmarkPetPassedAwayCommand(ctx=ctx, pet_id=pet_id))
    return PetDetailSchema.of(view)
