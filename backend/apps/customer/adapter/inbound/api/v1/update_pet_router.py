from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.adapter.inbound.api.schemas.update_pet_schema import UpdatePetRequestSchema
from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.ports.input.update_pet_use_case import UpdatePetUseCase
from customer.dependencies.update_pet_provider import get_update_pet_use_case
from hub.app.dtos.shop_context import ShopContext

update_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@update_pet_router.put("/{shop_id}/pets/{pet_id}", response_model=PetDetailSchema)
async def update_pet(
    pet_id: PetId,
    body: UpdatePetRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: UpdatePetUseCase = Depends(get_update_pet_use_case),
) -> PetDetailSchema:
    view = await use_case.update_pet(UpdatePetCommand(ctx=ctx, pet_id=pet_id, pet=body.to_input(),
                                                        intake_answer_id=body.intake_answer_id))
    return PetDetailSchema.of(view)
