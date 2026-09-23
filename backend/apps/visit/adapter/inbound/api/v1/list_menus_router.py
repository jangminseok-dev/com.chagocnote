from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_menus_schema import MenuListSchema, MenuSchema
from visit.app.dtos.list_menus_dto import ListMenusQuery
from visit.app.ports.input.list_menus_use_case import ListMenusUseCase
from visit.dependencies.list_menus_provider import get_list_menus_use_case

list_menus_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_menus_router.get("/{shop_id}/menus", response_model=MenuListSchema)
async def list_menus(
    include_archived: bool = False,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListMenusUseCase = Depends(get_list_menus_use_case),
) -> MenuListSchema:
    views = await use_case.list_menus(ListMenusQuery(ctx=ctx, include_archived=include_archived))
    return MenuListSchema(items=[MenuSchema.of(v) for v in views])
