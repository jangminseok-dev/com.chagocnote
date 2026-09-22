from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.app.dtos.delete_pet_dto import DeletePetCommand
from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
from customer.dependencies.delete_pet_provider import get_delete_pet_use_case
from hub.app.dtos.shop_context import ShopContext

delete_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@delete_pet_router.delete("/{shop_id}/pets/{pet_id}", status_code=204)
async def delete_pet(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: DeletePetUseCase = Depends(get_delete_pet_use_case),
) -> Response:
    await use_case.delete_pet(DeletePetCommand(ctx=ctx, pet_id=pet_id))
    return Response(status_code=204)
