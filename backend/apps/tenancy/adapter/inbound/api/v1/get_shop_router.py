from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.get_shop_schema import ShopResponseSchema
from tenancy.app.dtos.get_shop_dto import GetShopQuery
from tenancy.app.ports.input.get_shop_use_case import GetShopUseCase
from tenancy.dependencies.get_shop_provider import get_get_shop_use_case

get_shop_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@get_shop_router.get("/{shop_id}/settings", response_model=ShopResponseSchema)
async def get_shop(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetShopUseCase = Depends(get_get_shop_use_case),
) -> ShopResponseSchema:
    return ShopResponseSchema.of(await use_case.get_shop(GetShopQuery(ctx=ctx)))
