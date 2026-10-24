from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from notification.adapter.inbound.api.schemas.notification_overview_schema import NotificationOverviewSchema
from notification.adapter.inbound.api.schemas.update_notification_settings_schema import (
    UpdateNotificationSettingsRequestSchema,
)
from notification.app.dtos.update_notification_settings_dto import UpdateNotificationSettingsCommand
from notification.app.ports.input.update_notification_settings_use_case import UpdateNotificationSettingsUseCase
from notification.dependencies.update_notification_settings_provider import (
    get_update_notification_settings_use_case,
)

update_notification_settings_router = APIRouter(prefix="/v1/shops", tags=["notifications"])


@update_notification_settings_router.put("/{shop_id}/notification/settings", response_model=NotificationOverviewSchema)
async def update_notification_settings(
    body: UpdateNotificationSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateNotificationSettingsUseCase = Depends(get_update_notification_settings_use_case),
) -> NotificationOverviewSchema:
    view = await use_case.update_notification_settings(UpdateNotificationSettingsCommand(
        ctx=ctx, settings=body.to_settings(), sms_fallback_enabled=body.sms_fallback_enabled))
    return NotificationOverviewSchema.of(view, ctx.timezone)
