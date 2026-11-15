from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.consent_schema import SignatureBriefsSchema
from customer.app.dtos.list_pet_consent_signatures_dto import ListPetConsentSignaturesQuery
from customer.app.ports.input.list_pet_consent_signatures_use_case import ListPetConsentSignaturesUseCase
from customer.dependencies.list_pet_consent_signatures_provider import get_list_pet_consent_signatures_use_case
from hub.app.dtos.shop_context import ShopContext

list_pet_consent_signatures_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@list_pet_consent_signatures_router.get(
    "/{shop_id}/pets/{pet_id}/consent-signatures", response_model=SignatureBriefsSchema)
async def list_pet_consent_signatures(
    pet_id: PetId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListPetConsentSignaturesUseCase = Depends(get_list_pet_consent_signatures_use_case),
) -> SignatureBriefsSchema:
    views = await use_case.list_pet_consent_signatures(ListPetConsentSignaturesQuery(ctx=ctx, pet_id=pet_id))
    return SignatureBriefsSchema.of(views)
