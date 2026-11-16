from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.revisit_settings_schema import (
    RevisitSettingsSchema,
    UpdateRevisitSettingsRequestSchema,
)
from visit.app.dtos.update_revisit_settings_dto import UpdateRevisitSettingsCommand
from visit.app.ports.input.update_revisit_settings_use_case import UpdateRevisitSettingsUseCase
from visit.dependencies.update_revisit_settings_provider import get_update_revisit_settings_use_case

update_revisit_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_revisit_settings_router.put("/{shop_id}/revisit-settings", response_model=RevisitSettingsSchema)
async def update_revisit_settings(
    body: UpdateRevisitSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateRevisitSettingsUseCase = Depends(get_update_revisit_settings_use_case),
) -> RevisitSettingsSchema:
    saved = await use_case.update_revisit_settings(UpdateRevisitSettingsCommand(ctx=ctx, changes=body.changes()))
    return RevisitSettingsSchema.of(saved)
