from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_settings import NotificationSettings


@dataclass(frozen=True)
class UpdateNotificationSettingsCommand:
    """알림톡 설정 전체를 바꾼다(PUT). 문자 대체는 채널 줄의 칸이라 따로 든다."""

    ctx: ShopContext
    settings: NotificationSettings
    sms_fallback_enabled: bool
