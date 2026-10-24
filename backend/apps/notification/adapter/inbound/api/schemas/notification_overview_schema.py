"""한눈에 보기 응답 — 칸을 하나하나 적는다. 업체 쪽 ID(provider_channel_id·provider_template_id)는 내보내지 않는다(N12)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from notification.app.dtos.notification_overview_dto import NotificationOverviewView
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate

CHANNEL_NONE = "none"


def _local(at: datetime | None, zone: ZoneInfo) -> datetime | None:
    return at.astimezone(zone) if at is not None else None


class NotificationChannelSchema(BaseModel):
    status: str                    # none · token_requested · linked · unlinked
    linked_at: datetime | None     # 매장 시간대
    sender_number: str | None
    sender_verified: bool
    sms_fallback_enabled: bool

    @classmethod
    def of(cls, channel: NotificationChannel | None, zone: ZoneInfo) -> NotificationChannelSchema:
        if channel is None:
            return cls(status=CHANNEL_NONE, linked_at=None, sender_number=None, sender_verified=False,
                       sms_fallback_enabled=False)
        return cls(status=channel.status, linked_at=_local(channel.linked_at, zone),
                   sender_number=channel.sender_number,
                   sender_verified=channel.sender_number_verified_at is not None,
                   sms_fallback_enabled=channel.sms_fallback_enabled)


class NotificationSettingsSchema(BaseModel):
    confirm_enabled: bool
    reminder_enabled: bool
    report_enabled: bool
    change_enabled: bool
    next_visit_enabled: bool
    reminder_time: str             # "HH:MM"
    next_visit_after_weeks: int | None
    next_visit_cooldown_days: int

    @classmethod
    def of(cls, settings: NotificationSettings) -> NotificationSettingsSchema:
        return cls(confirm_enabled=settings.confirm_enabled, reminder_enabled=settings.reminder_enabled,
                   report_enabled=settings.report_enabled, change_enabled=settings.change_enabled,
                   next_visit_enabled=settings.next_visit_enabled,
                   reminder_time=settings.reminder_time.strftime("%H:%M"),
                   next_visit_after_weeks=settings.next_visit_after_weeks,
                   next_visit_cooldown_days=settings.next_visit_cooldown_days)


class NotificationTemplateSchema(BaseModel):
    kind: str
    status: str                    # pending · approved · rejected
    rejected_reason: str | None
    requested_at: datetime         # 매장 시간대
    decided_at: datetime | None

    @classmethod
    def of(cls, template: NotificationTemplate, zone: ZoneInfo) -> NotificationTemplateSchema:
        return cls(kind=template.kind, status=template.status, rejected_reason=template.rejected_reason,
                   requested_at=template.requested_at.astimezone(zone), decided_at=_local(template.decided_at, zone))


class NotificationOverviewSchema(BaseModel):
    channel: NotificationChannelSchema
    settings: NotificationSettingsSchema | None   # 연동 전엔 null
    templates: list[NotificationTemplateSchema]   # 종류 순

    @classmethod
    def of(cls, view: NotificationOverviewView, tz: str) -> NotificationOverviewSchema:
        zone = ZoneInfo(tz)
        return cls(
            channel=NotificationChannelSchema.of(view.channel, zone),
            settings=NotificationSettingsSchema.of(view.settings) if view.settings is not None else None,
            templates=[NotificationTemplateSchema.of(t, zone) for t in view.templates],
        )
