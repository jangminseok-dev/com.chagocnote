from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.set_pet_grooming_cycle_schema import SetPetGroomingCycleRequestSchema
from customer.app.dtos.set_pet_grooming_cycle_dto import SetPetGroomingCycleCommand
from customer.app.ports.input.set_pet_grooming_cycle_use_case import SetPetGroomingCycleUseCase
from customer.dependencies.set_pet_grooming_cycle_provider import get_set_pet_grooming_cycle_use_case
from hub.app.dtos.shop_context import ShopContext

set_pet_grooming_cycle_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@set_pet_grooming_cycle_router.put("/{shop_id}/pets/{pet_id}/grooming-cycle", status_code=204)
async def set_pet_grooming_cycle(
    pet_id: PetId,
    body: SetPetGroomingCycleRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: SetPetGroomingCycleUseCase = Depends(get_set_pet_grooming_cycle_use_case),
) -> Response:
    await use_case.set_pet_grooming_cycle(SetPetGroomingCycleCommand(ctx=ctx, pet_id=pet_id, weeks=body.weeks))
    return Response(status_code=204)


@set_pet_grooming_cycle_router.delete("/{shop_id}/pets/{pet_id}/grooming-cycle", status_code=204)
async def clear_pet_grooming_cycle(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: SetPetGroomingCycleUseCase = Depends(get_set_pet_grooming_cycle_use_case),
) -> Response:
    await use_case.set_pet_grooming_cycle(SetPetGroomingCycleCommand(ctx=ctx, pet_id=pet_id, weeks=None))
    return Response(status_code=204)
