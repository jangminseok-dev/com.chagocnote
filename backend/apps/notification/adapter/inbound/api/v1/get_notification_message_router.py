from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.path_params import MessageId
from notification.adapter.inbound.api.schemas.notification_message_schema import MessageItemSchema
from notification.app.dtos.get_notification_message_dto import GetNotificationMessageQuery
from notification.app.ports.input.get_notification_message_use_case import GetNotificationMessageUseCase
from notification.dependencies.get_notification_message_provider import get_get_notification_message_use_case

get_notification_message_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@get_notification_message_router.get("/{shop_id}/notifications/{message_id}", response_model=MessageItemSchema)
async def get_notification_message(
    message_id: MessageId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetNotificationMessageUseCase = Depends(get_get_notification_message_use_case),
) -> MessageItemSchema:
    view = await use_case.get_notification_message(GetNotificationMessageQuery(ctx=ctx, message_id=message_id))
    return MessageItemSchema.of(view, ctx.timezone)
