from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.app.dtos.clear_pet_grooming_consent_dto import ClearPetGroomingConsentCommand
from customer.app.ports.input.clear_pet_grooming_consent_use_case import ClearPetGroomingConsentUseCase
from customer.dependencies.clear_pet_grooming_consent_provider import get_clear_pet_grooming_consent_use_case
from hub.app.dtos.shop_context import ShopContext

clear_pet_grooming_consent_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@clear_pet_grooming_consent_router.delete("/{shop_id}/pets/{pet_id}/grooming-consent", response_model=PetDetailSchema)
async def clear_pet_grooming_consent(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: ClearPetGroomingConsentUseCase = Depends(get_clear_pet_grooming_consent_use_case),
) -> PetDetailSchema:
    view = await use_case.clear_pet_grooming_consent(ClearPetGroomingConsentCommand(ctx=ctx, pet_id=pet_id))
    return PetDetailSchema.of(view)
