from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.link_channel_schema import LinkChannelRequestSchema
from notification.adapter.inbound.api.schemas.notification_overview_schema import NotificationOverviewSchema
from notification.app.dtos.link_channel_dto import LinkChannelCommand
from notification.app.ports.input.link_channel_use_case import LinkChannelUseCase
from notification.dependencies.link_channel_provider import get_link_channel_use_case

link_channel_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@link_channel_router.post("/{shop_id}/notification/channel", response_model=NotificationOverviewSchema)
async def link_channel(
    body: LinkChannelRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: LinkChannelUseCase = Depends(get_link_channel_use_case),
) -> NotificationOverviewSchema:
    view = await use_case.link_channel(LinkChannelCommand(
        ctx=ctx, search_id=body.search_id, admin_phone=body.admin_phone, category_code=body.category_code,
        token=body.token))
    return NotificationOverviewSchema.of(view, ctx.timezone)
