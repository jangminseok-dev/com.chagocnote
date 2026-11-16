from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.schemas.consent_schema import SignConsentRequestSchema, SignedSchema
from customer.app.dtos.sign_consent_in_shop_dto import SignConsentInShopCommand
from customer.app.ports.input.sign_consent_in_shop_use_case import SignConsentInShopUseCase
from customer.dependencies.sign_consent_in_shop_provider import get_sign_consent_in_shop_use_case
from hub.app.dtos.shop_context import ShopContext

sign_consent_in_shop_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@sign_consent_in_shop_router.post("/{shop_id}/consent-signatures", response_model=SignedSchema, status_code=201)
async def sign_consent_in_shop(
    body: SignConsentRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: SignConsentInShopUseCase = Depends(get_sign_consent_in_shop_use_case),
) -> SignedSchema:
    signature_id = await use_case.sign_consent_in_shop(SignConsentInShopCommand(
        ctx=ctx, pet_ids=tuple(body.pet_ids), doc_digest=body.doc_digest, signer_name=body.signer_name,
        signature_png=body.png(), for_date=body.for_date,
    ))
    return SignedSchema(signature_id=signature_id)
