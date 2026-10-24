from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.notification_overview_schema import NotificationOverviewSchema
from notification.app.dtos.get_notification_overview_dto import GetNotificationOverviewQuery
from notification.app.ports.input.get_notification_overview_use_case import GetNotificationOverviewUseCase
from notification.dependencies.get_notification_overview_provider import get_get_notification_overview_use_case

get_notification_overview_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@get_notification_overview_router.get("/{shop_id}/notification", response_model=NotificationOverviewSchema)
async def get_notification_overview(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetNotificationOverviewUseCase = Depends(get_get_notification_overview_use_case),
) -> NotificationOverviewSchema:
    view = await use_case.get_notification_overview(GetNotificationOverviewQuery(ctx=ctx))
    return NotificationOverviewSchema.of(view, ctx.timezone)
