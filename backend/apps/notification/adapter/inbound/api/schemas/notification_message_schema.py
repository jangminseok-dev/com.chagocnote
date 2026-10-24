"""발송 내역의 줄 하나(MessageItem) — 칸을 하나하나 적는다. variables(주소)·업체 메시지 ID·오류 코드·고객·반려동물 ID 는
내보내지 않는다(N12). 주소는 실패 줄의 share_text 문안에만 든다(설계 7.2)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from notification.app.dtos.notification_message_dto import NotificationMessageView


class MessageItemSchema(BaseModel):
    message_id: int
    kind: str
    status: str                    # scheduled · sending · accepted · sent · fallback_sent · failed · canceled
    channel_used: str | None       # alimtalk · sms · lms
    scheduled_at: datetime         # 매장 시간대
    sent_at: datetime | None
    error_kind: str | None         # transient · permanent
    canceled_reason: str | None
    requested_by_member_id: int | None
    share_text: str | None         # 실패 줄에만 — 문자용 문안

    @classmethod
    def of(cls, view: NotificationMessageView, tz: str) -> MessageItemSchema:
        m, zone = view.message, ZoneInfo(tz)
        return cls(
            message_id=m.id, kind=m.kind, status=m.status, channel_used=m.channel_used,
            scheduled_at=m.scheduled_at.astimezone(zone),
            sent_at=m.sent_at.astimezone(zone) if m.sent_at is not None else None,
            error_kind=m.error_kind, canceled_reason=m.canceled_reason,
            requested_by_member_id=m.requested_by_member_id, share_text=view.share_text,
        )


class MessageListSchema(BaseModel):
    items: list[MessageItemSchema]   # 최신순

    @classmethod
    def of(cls, views: list[NotificationMessageView], tz: str) -> MessageListSchema:
        return cls(items=[MessageItemSchema.of(v, tz) for v in views])
