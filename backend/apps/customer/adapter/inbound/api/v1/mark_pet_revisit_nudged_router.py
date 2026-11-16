from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.app.dtos.mark_pet_revisit_nudged_dto import MarkPetRevisitNudgedCommand
from customer.app.ports.input.mark_pet_revisit_nudged_use_case import MarkPetRevisitNudgedUseCase
from customer.dependencies.mark_pet_revisit_nudged_provider import get_mark_pet_revisit_nudged_use_case
from hub.app.dtos.shop_context import ShopContext

mark_pet_revisit_nudged_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@mark_pet_revisit_nudged_router.put("/{shop_id}/pets/{pet_id}/revisit-nudge", status_code=204)
async def mark_pet_revisit_nudged(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: MarkPetRevisitNudgedUseCase = Depends(get_mark_pet_revisit_nudged_use_case),
) -> Response:
    await use_case.mark_pet_revisit_nudged(MarkPetRevisitNudgedCommand(ctx=ctx, pet_id=pet_id))
    return Response(status_code=204)
