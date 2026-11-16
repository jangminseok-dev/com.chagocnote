from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.consent_text_schema import ConsentTextsSchema
from customer.app.dtos.list_consent_texts_dto import ListConsentTextsQuery
from customer.app.ports.input.list_consent_texts_use_case import ListConsentTextsUseCase
from customer.dependencies.list_consent_texts_provider import get_list_consent_texts_use_case
from hub.app.dtos.shop_context import ShopContext

list_consent_texts_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@list_consent_texts_router.get("/{shop_id}/consent-texts", response_model=ConsentTextsSchema)
async def list_consent_texts(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListConsentTextsUseCase = Depends(get_list_consent_texts_use_case),
) -> ConsentTextsSchema:
    return ConsentTextsSchema.of(await use_case.list_consent_texts(ListConsentTextsQuery(ctx=ctx)))
