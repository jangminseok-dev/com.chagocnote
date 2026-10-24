"""notification 테스트가 함께 쓰는 값 — 매장 컨텍스트와 채널·설정·템플릿·메시지 엔티티를 짧게 만든다."""
from __future__ import annotations

from datetime import datetime, time, timezone

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.value_objects.channel_status import LINKED
from notification.domain.value_objects.message_kind import CONFIRM
from notification.domain.value_objects.message_status import SCHEDULED
from notification.domain.value_objects.new_message import NewMessage
from notification.domain.value_objects.template_status import APPROVED

STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
OWNER_PERMISSIONS = STAFF_PERMISSIONS | frozenset(
    {"sales:read", "record:delete", "customer:delete", "member:manage", "shop:update"}
)
TZ = "Asia/Seoul"


def kst(month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """2026년 한국 시각을 UTC 로. 테스트의 모든 시각은 이것으로 만든다."""
    from zoneinfo import ZoneInfo

    return datetime(2026, month, day, hour, minute, tzinfo=ZoneInfo(TZ)).astimezone(timezone.utc)


def ctx(shop_id: int = 1, member_id: int = 11, role: str = "owner") -> ShopContext:
    permissions = OWNER_PERMISSIONS if role == "owner" else STAFF_PERMISSIONS
    return ShopContext(shop_id=shop_id, member_id=member_id, role=role, permissions=permissions,
                       timezone=TZ)


def settings(**overrides) -> NotificationSettings:
    fields = dict(
        confirm_enabled=True, reminder_enabled=True, report_enabled=True, change_enabled=True,
        next_visit_enabled=False, reminder_time=time(18, 0), next_visit_after_weeks=None,
        next_visit_cooldown_days=30,
    )
    fields.update(overrides)
    return NotificationSettings(**fields)


def channel(**overrides) -> NotificationChannel:
    fields = dict(
        shop_id=1, status=LINKED, provider="solapi", provider_channel_id="KA01PF0001",
        linked_at=kst(10, 1, 10), unlinked_at=None, sender_number=None,
        sender_number_verified_at=None, sms_fallback_enabled=False,
    )
    fields.update(overrides)
    return NotificationChannel(**fields)


def template(**overrides) -> NotificationTemplate:
    fields = dict(
        id=1, shop_id=1, kind=CONFIRM, text_version=1, provider_template_id="KA01TP0001",
        status=APPROVED, rejected_reason=None, requested_at=kst(10, 1, 10), decided_at=kst(10, 2, 10),
    )
    fields.update(overrides)
    return NotificationTemplate(**fields)


def message(**overrides) -> NotificationMessage:
    fields = dict(
        id=1, shop_id=1, visit_id=1, customer_id=1, pet_id=None, kind=CONFIRM, scheduled_at=kst(10, 14, 11),
        status=SCHEDULED, attempts=0, next_attempt_at=None, channel_used=None, provider_message_id=None,
        error_code=None, error_kind=None, variables={}, requested_by_member_id=None,
        created_at=kst(10, 14, 11), sent_at=None, canceled_reason=None,
    )
    fields.update(overrides)
    return NotificationMessage(**fields)


def new_message(**overrides) -> NewMessage:
    fields = dict(
        shop_id=1, visit_id=1, customer_id=1, pet_id=None, kind=CONFIRM, scheduled_at=kst(10, 14, 11), variables={},
        requested_by_member_id=None,
    )
    fields.update(overrides)
    return NewMessage(**fields)
