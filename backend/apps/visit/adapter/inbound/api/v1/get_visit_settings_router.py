from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_settings_schema import VisitSettingsSchema
from visit.app.dtos.get_visit_settings_dto import GetVisitSettingsQuery
from visit.app.ports.input.get_visit_settings_use_case import GetVisitSettingsUseCase
from visit.dependencies.get_visit_settings_provider import get_get_visit_settings_use_case

get_visit_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_settings_router.get("/{shop_id}/visit-settings", response_model=VisitSettingsSchema)
async def get_visit_settings(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitSettingsUseCase = Depends(get_get_visit_settings_use_case),
) -> VisitSettingsSchema:
    return VisitSettingsSchema.of(await use_case.get_visit_settings(GetVisitSettingsQuery(ctx=ctx)))
