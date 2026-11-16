from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.form_settings_schema import FormSettingsSchema
from customer.app.dtos.get_form_settings_dto import GetFormSettingsQuery
from customer.app.ports.input.get_form_settings_use_case import GetFormSettingsUseCase
from customer.dependencies.get_form_settings_provider import get_get_form_settings_use_case
from hub.app.dtos.shop_context import ShopContext

get_form_settings_router = APIRouter(prefix="/v1/shops", tags=["forms"])


@get_form_settings_router.get("/{shop_id}/form-settings", response_model=FormSettingsSchema)
async def get_form_settings(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetFormSettingsUseCase = Depends(get_get_form_settings_use_case),
) -> FormSettingsSchema:
    return FormSettingsSchema.of(await use_case.get_form_settings(GetFormSettingsQuery(ctx=ctx)))
