from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from notification.app.dtos.get_notification_message_dto import GetNotificationMessageQuery
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.app.ports.input.get_notification_message_use_case import GetNotificationMessageUseCase
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.services.message_text import message_views
from notification.domain.errors import MessageNotFoundError


class GetNotificationMessageInteractor(GetNotificationMessageUseCase):
    """줄 하나(알림장 보내기 직후 폴링용, 설계 8.3). 없거나 다른 매장이면 404(N1)."""

    def __init__(self, messages: MessageRepository, shops: ShopProfilePort, directory: CustomerDirectoryPort) -> None:
        self._messages = messages
        self._shops = shops
        self._directory = directory

    async def get_notification_message(self, query: GetNotificationMessageQuery) -> NotificationMessageView:
        row = await self._messages.get(query.ctx, query.message_id)
        if row is None:
            raise MessageNotFoundError("그 알림이 없습니다.")
        [view] = await message_views(query.ctx, [row], self._shops, self._directory)
        return view
