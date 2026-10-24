from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_settings import NotificationSettings


class SettingsRepository(ABC):
    """매장의 알림톡 설정 한 줄(notification_settings). 매장 범위."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> NotificationSettings | None:
        """연동 전(행이 없으면) None."""

    @abstractmethod
    async def ensure(self, ctx: ShopContext) -> NotificationSettings:
        """없으면 DEFAULT_NOTIFICATION_SETTINGS 로 만든다. 있으면 그대로 돌려준다."""

    @abstractmethod
    async def update(self, ctx: ShopContext, settings: NotificationSettings) -> NotificationSettings:
        """행이 있어야 한다(ensure 뒤). 범위 검사는 도메인(check_settings)과 DB CHECK 가 한다."""
