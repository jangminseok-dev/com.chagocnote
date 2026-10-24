from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from notification.app.dtos.unlink_channel_dto import UnlinkChannelCommand
from notification.app.ports.input.unlink_channel_use_case import UnlinkChannelUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.errors import ChannelNotLinkedError
from notification.domain.value_objects.channel_status import UNLINKED


class UnlinkChannelInteractor(UnlinkChannelUseCase):
    """연동을 푼다(설계 6.2-5) — unlinked, 템플릿 삭제, 대기 줄 전부 channel_unlinked. 업체에는 아무것도 보내지 않는다.

    발신번호·인증 시각·문자 대체는 남긴다 — 다시 연동하면 그대로 쓴다.
    """

    def __init__(
        self, channels: ChannelRepository, templates: TemplateRepository, messages: MessageRepository,
        now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._templates = templates
        self._messages = messages
        self._now = now

    async def unlink_channel(self, command: UnlinkChannelCommand) -> None:
        ctx = command.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            raise ChannelNotLinkedError("연동된 채널이 없습니다.")
        await self._channels.save(ctx, replace(channel, status=UNLINKED, unlinked_at=self._now(),
                                               provider_channel_id=None))
        await self._templates.delete_all(ctx)
        await self._messages.cancel_pending(ctx, "channel_unlinked")
