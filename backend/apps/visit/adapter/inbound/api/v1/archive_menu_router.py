from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import MenuId
from visit.adapter.inbound.api.schemas.list_menus_schema import MenuSchema
from visit.app.dtos.archive_menu_dto import ArchiveMenuCommand
from visit.app.ports.input.archive_menu_use_case import ArchiveMenuUseCase
from visit.dependencies.archive_menu_provider import get_archive_menu_use_case

archive_menu_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@archive_menu_router.post("/{shop_id}/menus/{menu_id}/archive", response_model=MenuSchema)
async def archive_menu(
    menu_id: MenuId,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: ArchiveMenuUseCase = Depends(get_archive_menu_use_case),
) -> MenuSchema:
    return MenuSchema.of(await use_case.archive_menu(ArchiveMenuCommand(ctx=ctx, menu_id=menu_id)))
