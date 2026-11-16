from typing import Literal

from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.schemas.consent_text_schema import (
    ConsentTextSchema, UpdateConsentTextRequestSchema,
)
from customer.app.dtos.update_consent_text_dto import UpdateConsentTextCommand
from customer.app.ports.input.update_consent_text_use_case import UpdateConsentTextUseCase
from customer.dependencies.update_consent_text_provider import get_update_consent_text_use_case
from hub.app.dtos.shop_context import ShopContext

update_consent_text_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@update_consent_text_router.put("/{shop_id}/consent-texts/{part}", response_model=ConsentTextSchema)
async def update_consent_text(
    part: Literal["basic", "senior", "condition"],
    body: UpdateConsentTextRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateConsentTextUseCase = Depends(get_update_consent_text_use_case),
) -> ConsentTextSchema:
    view = await use_case.update_consent_text(UpdateConsentTextCommand(ctx=ctx, part=part, body=body.body))
    return ConsentTextSchema.of(view)
