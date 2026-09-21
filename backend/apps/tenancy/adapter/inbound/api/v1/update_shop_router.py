from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.get_shop_schema import ShopResponseSchema
from tenancy.adapter.inbound.api.schemas.update_shop_schema import UpdateShopRequestSchema
from tenancy.app.dtos.update_shop_dto import UpdateShopCommand
from tenancy.app.ports.input.update_shop_use_case import UpdateShopUseCase
from tenancy.dependencies.update_shop_provider import get_update_shop_use_case

update_shop_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@update_shop_router.put("/{shop_id}/settings", response_model=ShopResponseSchema)
async def update_shop(
    body: UpdateShopRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateShopUseCase = Depends(get_update_shop_use_case),
) -> ShopResponseSchema:
    view = await use_case.update_shop(
        UpdateShopCommand(
            ctx=ctx, name=body.name, phone=body.phone or None, address=body.address or None
        )
    )
    return ShopResponseSchema.of(view)
