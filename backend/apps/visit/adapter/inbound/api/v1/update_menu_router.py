from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import MenuId
from visit.adapter.inbound.api.schemas.list_menus_schema import MenuSchema
from visit.adapter.inbound.api.schemas.update_menu_schema import UpdateMenuRequestSchema
from visit.app.dtos.update_menu_dto import UpdateMenuCommand
from visit.app.ports.input.update_menu_use_case import UpdateMenuUseCase
from visit.dependencies.update_menu_provider import get_update_menu_use_case

update_menu_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_menu_router.put("/{shop_id}/menus/{menu_id}", response_model=MenuSchema)
async def update_menu(
    menu_id: MenuId,
    body: UpdateMenuRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateMenuUseCase = Depends(get_update_menu_use_case),
) -> MenuSchema:
    view = await use_case.update_menu(
        UpdateMenuCommand(ctx=ctx, menu_id=menu_id, name=body.name,
                          default_duration_minutes=body.default_duration_minutes, sort_order=body.sort_order,
                          price=body.price)
    )
    return MenuSchema.of(view)
