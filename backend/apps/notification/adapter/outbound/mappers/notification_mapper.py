"""네 엔티티 ↔ ORM. 채널은 upsert 의 값 사전도 여기서 만든다."""
from __future__ import annotations

from notification.adapter.outbound.orm.notification_orm import (
    NotificationChannelOrm,
    NotificationMessageOrm,
    NotificationSettingsOrm,
    NotificationTemplateOrm,
)
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate


def to_channel(orm: NotificationChannelOrm) -> NotificationChannel:
    return NotificationChannel(
        shop_id=orm.shop_id, status=orm.status, provider=orm.provider, provider_channel_id=orm.provider_channel_id,
        linked_at=orm.linked_at, unlinked_at=orm.unlinked_at, sender_number=orm.sender_number,
        sender_number_verified_at=orm.sender_number_verified_at, sms_fallback_enabled=orm.sms_fallback_enabled,
    )


def channel_values(channel: NotificationChannel) -> dict:
    """INSERT 와 ON CONFLICT UPDATE 가 함께 쓰는, 키(shop_id)를 뺀 칸."""
    return dict(
        status=channel.status, provider=channel.provider, provider_channel_id=channel.provider_channel_id,
        linked_at=channel.linked_at, unlinked_at=channel.unlinked_at, sender_number=channel.sender_number,
        sender_number_verified_at=channel.sender_number_verified_at, sms_fallback_enabled=channel.sms_fallback_enabled,
    )


def to_settings(orm: NotificationSettingsOrm) -> NotificationSettings:
    return NotificationSettings(
        confirm_enabled=orm.confirm_enabled, reminder_enabled=orm.reminder_enabled, report_enabled=orm.report_enabled,
        change_enabled=orm.change_enabled, next_visit_enabled=orm.next_visit_enabled, reminder_time=orm.reminder_time,
        next_visit_after_weeks=orm.next_visit_after_weeks, next_visit_cooldown_days=orm.next_visit_cooldown_days,
    )


def settings_values(settings: NotificationSettings) -> dict:
    return dict(
        confirm_enabled=settings.confirm_enabled, reminder_enabled=settings.reminder_enabled,
        report_enabled=settings.report_enabled, change_enabled=settings.change_enabled,
        next_visit_enabled=settings.next_visit_enabled, reminder_time=settings.reminder_time,
        next_visit_after_weeks=settings.next_visit_after_weeks,
        next_visit_cooldown_days=settings.next_visit_cooldown_days,
    )


def to_template(orm: NotificationTemplateOrm) -> NotificationTemplate:
    return NotificationTemplate(
        id=orm.id, shop_id=orm.shop_id, kind=orm.kind, text_version=orm.text_version,
        provider_template_id=orm.provider_template_id, status=orm.status, rejected_reason=orm.rejected_reason,
        requested_at=orm.requested_at, decided_at=orm.decided_at,
        pending_text_version=orm.pending_text_version,
        pending_provider_template_id=orm.pending_provider_template_id,
    )


def to_message(orm: NotificationMessageOrm) -> NotificationMessage:
    return NotificationMessage(
        id=orm.id, shop_id=orm.shop_id, visit_id=orm.visit_id, customer_id=orm.customer_id, pet_id=orm.pet_id,
        kind=orm.kind, scheduled_at=orm.scheduled_at, status=orm.status, attempts=orm.attempts,
        next_attempt_at=orm.next_attempt_at, channel_used=orm.channel_used,
        provider_message_id=orm.provider_message_id, error_code=orm.error_code, error_kind=orm.error_kind,
        variables=dict(orm.variables), requested_by_member_id=orm.requested_by_member_id,
        created_at=orm.created_at, sent_at=orm.sent_at, canceled_reason=orm.canceled_reason,
    )
