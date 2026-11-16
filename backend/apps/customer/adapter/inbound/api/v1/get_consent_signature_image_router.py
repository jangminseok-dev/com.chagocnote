from fastapi import APIRouter, Depends, Response

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.path_params import SignatureId
from customer.app.dtos.get_consent_signature_image_dto import GetConsentSignatureImageQuery
from customer.app.ports.input.get_consent_signature_image_use_case import GetConsentSignatureImageUseCase
from customer.dependencies.get_consent_signature_image_provider import get_get_consent_signature_image_use_case
from hub.app.dtos.shop_context import ShopContext

get_consent_signature_image_router = APIRouter(prefix="/v1/shops", tags=["forms"])

# 서버는 그림을 풀지 않았다 — 브라우저가 다른 형으로 읽지 못하게 하고 어디에도 남기지 않는다.
_IMAGE_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"}


@get_consent_signature_image_router.get("/{shop_id}/consent-signatures/{signature_id}/image")
async def get_consent_signature_image(
    signature_id: SignatureId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetConsentSignatureImageUseCase = Depends(get_get_consent_signature_image_use_case),
) -> Response:
    raw = await use_case.get_consent_signature_image(GetConsentSignatureImageQuery(ctx=ctx, signature_id=signature_id))
    return Response(content=raw, media_type="image/png", headers=_IMAGE_HEADERS)
