from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.revisit_settings_schema import RevisitSettingsSchema
from visit.app.dtos.get_revisit_settings_dto import GetRevisitSettingsQuery
from visit.app.ports.input.get_revisit_settings_use_case import GetRevisitSettingsUseCase
from visit.dependencies.get_revisit_settings_provider import get_get_revisit_settings_use_case

get_revisit_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_revisit_settings_router.get("/{shop_id}/revisit-settings", response_model=RevisitSettingsSchema)
async def get_revisit_settings(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetRevisitSettingsUseCase = Depends(get_get_revisit_settings_use_case),
) -> RevisitSettingsSchema:
    return RevisitSettingsSchema.of(await use_case.get_revisit_settings(GetRevisitSettingsQuery(ctx=ctx)))
