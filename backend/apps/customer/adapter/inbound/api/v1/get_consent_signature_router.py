from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.path_params import SignatureId
from customer.adapter.inbound.api.schemas.consent_schema import SignatureDetailSchema
from customer.app.dtos.get_consent_signature_dto import GetConsentSignatureQuery
from customer.app.ports.input.get_consent_signature_use_case import GetConsentSignatureUseCase
from customer.dependencies.get_consent_signature_provider import get_get_consent_signature_use_case
from hub.app.dtos.shop_context import ShopContext

get_consent_signature_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@get_consent_signature_router.get(
    "/{shop_id}/consent-signatures/{signature_id}", response_model=SignatureDetailSchema)
async def get_consent_signature(
    signature_id: SignatureId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetConsentSignatureUseCase = Depends(get_get_consent_signature_use_case),
) -> SignatureDetailSchema:
    view = await use_case.get_consent_signature(GetConsentSignatureQuery(ctx=ctx, signature_id=signature_id))
    return SignatureDetailSchema.of(view)
