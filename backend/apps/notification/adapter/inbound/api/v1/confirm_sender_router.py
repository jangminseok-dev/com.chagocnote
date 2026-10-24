from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.confirm_sender_schema import ConfirmSenderRequestSchema
from notification.adapter.inbound.api.schemas.notification_overview_schema import NotificationOverviewSchema
from notification.app.dtos.confirm_sender_dto import ConfirmSenderCommand
from notification.app.ports.input.confirm_sender_use_case import ConfirmSenderUseCase
from notification.dependencies.confirm_sender_provider import get_confirm_sender_use_case

confirm_sender_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@confirm_sender_router.post("/{shop_id}/notification/sender", response_model=NotificationOverviewSchema)
async def confirm_sender(
    body: ConfirmSenderRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: ConfirmSenderUseCase = Depends(get_confirm_sender_use_case),
) -> NotificationOverviewSchema:
    view = await use_case.confirm_sender(ConfirmSenderCommand(ctx=ctx, phone=body.phone, code=body.code))
    return NotificationOverviewSchema.of(view, ctx.timezone)
