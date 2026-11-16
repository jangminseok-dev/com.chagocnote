from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.consent_schema import ConsentDocumentSchema
from customer.app.dtos.get_consent_document_dto import GetConsentDocumentQuery
from customer.app.ports.input.get_consent_document_use_case import GetConsentDocumentUseCase
from customer.dependencies.get_consent_document_provider import get_get_consent_document_use_case
from hub.app.dtos.shop_context import ShopContext

get_consent_document_router = APIRouter(prefix="/v1/shops", tags=["forms"])

_MAX_BIGINT = 9_223_372_036_854_775_807


@get_consent_document_router.get("/{shop_id}/consent-document", response_model=ConsentDocumentSchema)
async def get_consent_document(
    pet_ids: Annotated[list[Annotated[int, Query(ge=1, le=_MAX_BIGINT)]], Query(min_length=1, max_length=10)],
    for_date: date | None = None,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetConsentDocumentUseCase = Depends(get_get_consent_document_use_case),
) -> ConsentDocumentSchema:
    view = await use_case.get_consent_document(GetConsentDocumentQuery(
        ctx=ctx, pet_ids=tuple(pet_ids), for_date=for_date))
    return ConsentDocumentSchema.of(view)
