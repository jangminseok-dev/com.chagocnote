from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.schemas.form_settings_schema import (
    FormSettingsSchema, UpdateFormSettingsRequestSchema,
)
from customer.app.dtos.update_form_settings_dto import UpdateFormSettingsCommand
from customer.app.ports.input.update_form_settings_use_case import UpdateFormSettingsUseCase
from customer.dependencies.update_form_settings_provider import get_update_form_settings_use_case
from hub.app.dtos.shop_context import ShopContext

update_form_settings_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@update_form_settings_router.put("/{shop_id}/form-settings", response_model=FormSettingsSchema)
async def update_form_settings(
    body: UpdateFormSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateFormSettingsUseCase = Depends(get_update_form_settings_use_case),
) -> FormSettingsSchema:
    settings = await use_case.update_form_settings(
        UpdateFormSettingsCommand(ctx=ctx, settings=body.to_settings(), kept=body.kept()))
    return FormSettingsSchema.of(settings)
