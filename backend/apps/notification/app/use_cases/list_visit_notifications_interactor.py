from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from notification.app.dtos.list_visit_notifications_dto import ListVisitNotificationsQuery
from notification.app.dtos.notification_message_dto import NotificationMessageView
from notification.app.ports.input.list_visit_notifications_use_case import ListVisitNotificationsUseCase
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.services.message_text import message_views


class ListVisitNotificationsInteractor(ListVisitNotificationsUseCase):
    """그 방문의 줄 전부, 최신순(설계 7.2). notification 은 방문 표를 모르므로 다른 매장의 방문이나 없는 방문은 빈 목록이다."""

    def __init__(self, messages: MessageRepository, shops: ShopProfilePort, directory: CustomerDirectoryPort) -> None:
        self._messages = messages
        self._shops = shops
        self._directory = directory

    async def list_visit_notifications(self, query: ListVisitNotificationsQuery) -> list[NotificationMessageView]:
        rows = await self._messages.list_for_visit(query.ctx, query.visit_id)
        return await message_views(query.ctx, rows, self._shops, self._directory)
