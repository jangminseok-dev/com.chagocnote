from __future__ import annotations

from dataclasses import dataclass

from notification.domain.entities.notification_message import NotificationMessage


@dataclass(frozen=True)
class NotificationMessageView:
    """발송 내역의 줄 하나. share_text 는 실패 줄의 문자용 문안(설계 7.2) — 그 밖은 None."""

    message: NotificationMessage
    share_text: str | None
