from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.path_params import MessageKind, VisitId
from notification.adapter.inbound.api.schemas.resend_notification_schema import MessageCreatedSchema
from notification.app.dtos.resend_notification_dto import ResendNotificationCommand
from notification.app.ports.input.resend_notification_use_case import ResendNotificationUseCase
from notification.dependencies.resend_notification_provider import get_resend_notification_use_case

resend_notification_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@resend_notification_router.post(
    "/{shop_id}/visits/{visit_id}/notifications/{kind}/resend", response_model=MessageCreatedSchema, status_code=201,
)
async def resend_notification(
    visit_id: VisitId,
    kind: MessageKind,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: ResendNotificationUseCase = Depends(get_resend_notification_use_case),
) -> MessageCreatedSchema:
    message_id = await use_case.resend_notification(ResendNotificationCommand(ctx=ctx, visit_id=visit_id, kind=kind))
    return MessageCreatedSchema(message_id=message_id)
