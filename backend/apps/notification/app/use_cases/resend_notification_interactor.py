from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from notification.app.dtos.resend_notification_dto import ResendNotificationCommand
from notification.app.ports.input.resend_notification_use_case import ResendNotificationUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.errors import (
    ChannelNotLinkedError,
    MessageAlreadyPendingError,
    MessageNotFoundError,
    TemplateNotApprovedError,
)
from notification.domain.value_objects.message_status import ACCEPTED, PENDING_STATUSES
from notification.domain.value_objects.new_message import NewMessage
from notification.domain.value_objects.template_status import APPROVED


class ResendNotificationInteractor(ResendNotificationUseCase):
    """[다시 보내기] — 매장이 직접 누른 것이니 설정은 보지 않는다(디스패처도 requested_by_member_id 가 있는 줄은 setting_off 를
    건너뛴다). 이 매장·방문·종류의 가장 최근 줄이 끝나 있어야 하고(취소·성공·실패), 그 줄의 재료로 지금 보낼 새 줄을 만든다.
    같은 방문·종류의 대기 줄은 하나(부분 유일 색인)라 동시에 두 번 눌러도 둘째는 409 다(N5)."""

    def __init__(
        self, channels: ChannelRepository, templates: TemplateRepository, messages: MessageRepository,
        now: Callable[[], datetime], wake: Callable[[], None],
    ) -> None:
        self._channels = channels
        self._templates = templates
        self._messages = messages
        self._now = now
        self._wake = wake

    async def resend_notification(self, command: ResendNotificationCommand) -> int:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("연동된 채널이 없습니다.")
        template = await self._templates.get(ctx, command.kind)
        if template is None or template.status != APPROVED:
            raise TemplateNotApprovedError("아직 승인되지 않은 종류입니다.")
        rows = await self._messages.list_for_visit(ctx, command.visit_id)
        latest = next((m for m in rows if m.kind == command.kind), None)
        if latest is None:
            raise MessageNotFoundError("다시 보낼 알림이 없습니다.")
        if latest.status in PENDING_STATUSES or latest.status == ACCEPTED:
            raise MessageAlreadyPendingError("같은 종류의 알림이 이미 보내는 중입니다.")
        created = await self._messages.create(ctx, NewMessage(
            shop_id=ctx.shop_id, visit_id=command.visit_id, customer_id=latest.customer_id, pet_id=latest.pet_id,
            kind=command.kind, scheduled_at=self._now(), variables=latest.variables,
            requested_by_member_id=ctx.member_id,
        ))
        self._wake()
        return created.id
