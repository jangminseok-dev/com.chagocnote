from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.adapter.inbound.api.schemas.set_pet_grooming_consent_schema import SetPetGroomingConsentRequestSchema
from customer.app.dtos.set_pet_grooming_consent_dto import SetPetGroomingConsentCommand
from customer.app.ports.input.set_pet_grooming_consent_use_case import SetPetGroomingConsentUseCase
from customer.dependencies.set_pet_grooming_consent_provider import get_set_pet_grooming_consent_use_case
from hub.app.dtos.shop_context import ShopContext

set_pet_grooming_consent_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@set_pet_grooming_consent_router.put("/{shop_id}/pets/{pet_id}/grooming-consent", response_model=PetDetailSchema)
async def set_pet_grooming_consent(
    pet_id: PetId,
    body: SetPetGroomingConsentRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: SetPetGroomingConsentUseCase = Depends(get_set_pet_grooming_consent_use_case),
) -> PetDetailSchema:
    view = await use_case.set_pet_grooming_consent(SetPetGroomingConsentCommand(ctx=ctx, pet_id=pet_id, received_on=body.received_on))
    return PetDetailSchema.of(view)
