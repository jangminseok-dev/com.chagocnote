from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_channel import NotificationChannel


class ChannelRepository(ABC):
    """매장의 채널 연동 한 줄(notification_channels). 매장 범위 — ShopContext 의 매장만 본다."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> NotificationChannel | None:
        """이 매장의 채널. 연동을 시작한 적이 없으면 None."""

    @abstractmethod
    async def save(self, ctx: ShopContext, channel: NotificationChannel) -> NotificationChannel:
        """shop_id 로 upsert 한다. channel.shop_id 가 ctx 의 매장과 다르면 ValueError."""
