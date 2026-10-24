from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.path_params import VisitId
from notification.adapter.inbound.api.schemas.notification_message_schema import MessageListSchema
from notification.app.dtos.list_visit_notifications_dto import ListVisitNotificationsQuery
from notification.app.ports.input.list_visit_notifications_use_case import ListVisitNotificationsUseCase
from notification.dependencies.list_visit_notifications_provider import get_list_visit_notifications_use_case

list_visit_notifications_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@list_visit_notifications_router.get("/{shop_id}/visits/{visit_id}/notifications", response_model=MessageListSchema)
async def list_visit_notifications(
    visit_id: VisitId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListVisitNotificationsUseCase = Depends(get_list_visit_notifications_use_case),
) -> MessageListSchema:
    views = await use_case.list_visit_notifications(ListVisitNotificationsQuery(ctx=ctx, visit_id=visit_id))
    return MessageListSchema.of(views, ctx.timezone)
