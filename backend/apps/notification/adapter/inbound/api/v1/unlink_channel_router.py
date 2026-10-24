from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.app.dtos.unlink_channel_dto import UnlinkChannelCommand
from notification.app.ports.input.unlink_channel_use_case import UnlinkChannelUseCase
from notification.dependencies.unlink_channel_provider import get_unlink_channel_use_case

unlink_channel_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@unlink_channel_router.delete("/{shop_id}/notification/channel", status_code=204)
async def unlink_channel(
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UnlinkChannelUseCase = Depends(get_unlink_channel_use_case),
) -> Response:
    await use_case.unlink_channel(UnlinkChannelCommand(ctx=ctx))
    return Response(status_code=204)
