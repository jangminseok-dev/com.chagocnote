from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.create_menu_schema import CreateMenuRequestSchema
from visit.adapter.inbound.api.schemas.list_menus_schema import MenuSchema
from visit.app.dtos.create_menu_dto import CreateMenuCommand
from visit.app.ports.input.create_menu_use_case import CreateMenuUseCase
from visit.dependencies.create_menu_provider import get_create_menu_use_case

create_menu_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@create_menu_router.post("/{shop_id}/menus", response_model=MenuSchema, status_code=201)
async def create_menu(
    body: CreateMenuRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: CreateMenuUseCase = Depends(get_create_menu_use_case),
) -> MenuSchema:
    view = await use_case.create_menu(
        CreateMenuCommand(ctx=ctx, name=body.name, default_duration_minutes=body.default_duration_minutes,
                          price=body.price)
    )
    return MenuSchema.of(view)
