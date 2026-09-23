from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_settings_schema import VisitSettingsSchema
from visit.adapter.inbound.api.schemas.update_visit_settings_schema import (
    UpdateVisitSettingsRequestSchema,
)
from visit.app.dtos.update_visit_settings_dto import UpdateVisitSettingsCommand
from visit.app.ports.input.update_visit_settings_use_case import UpdateVisitSettingsUseCase
from visit.dependencies.update_visit_settings_provider import get_update_visit_settings_use_case

update_visit_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_visit_settings_router.put("/{shop_id}/visit-settings", response_model=VisitSettingsSchema)
async def update_visit_settings(
    body: UpdateVisitSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateVisitSettingsUseCase = Depends(get_update_visit_settings_use_case),
) -> VisitSettingsSchema:
    view = await use_case.update_visit_settings(
        UpdateVisitSettingsCommand(ctx=ctx, settings=body.to_settings())
    )
    return VisitSettingsSchema.of(view)
