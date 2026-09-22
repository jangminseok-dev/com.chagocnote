from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand
from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
from customer.dependencies.mark_pet_passed_away_provider import get_mark_pet_passed_away_use_case
from hub.app.dtos.shop_context import ShopContext

mark_pet_passed_away_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@mark_pet_passed_away_router.post("/{shop_id}/pets/{pet_id}/passed-away", response_model=PetDetailSchema)
async def mark_pet_passed_away(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: MarkPetPassedAwayUseCase = Depends(get_mark_pet_passed_away_use_case),
) -> PetDetailSchema:
    view = await use_case.mark_pet_passed_away(MarkPetPassedAwayCommand(ctx=ctx, pet_id=pet_id))
    return PetDetailSchema.of(view)
