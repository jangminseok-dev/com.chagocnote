from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from notification.domain.value_objects.channel_status import CHANNEL_STATUSES
from notification.domain.value_objects.message_kind import KINDS
from notification.domain.value_objects.message_status import (
    CANCEL_REASONS,
    CHANNELS_USED,
    ERROR_KINDS,
    PENDING_STATUSES,
    STATUSES,
)
from notification.domain.value_objects.template_status import TEMPLATE_STATUSES


def _in(column: str, values: tuple[str, ...]) -> str:
    """CHECK 의 목록은 도메인 튜플에서 만든다. 마이그레이션 0011 은 글자로 적었으므로 값을 더하면 새 마이그레이션이다 —
    tests/integration/test_notification_schema.py 가 실제 DB 와 튜플을 대조한다."""
    return f"{column} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


_PENDING_IN = _in("status", tuple(s for s in STATUSES if s in PENDING_STATUSES))


class NotificationChannelOrm(Base):
    """매장의 카카오톡 채널 연동 한 줄(설계 4.1). shop_id 는 tenancy 의 ID — 외래 키 없음."""

    __tablename__ = "notification_channels"
    __table_args__ = (
        CheckConstraint(_in("status", CHANNEL_STATUSES), name="ck_notification_channels_status"),
        # 문자 대체는 발신번호 인증을 마쳐야 켤 수 있다(N11).
        CheckConstraint(
            "NOT sms_fallback_enabled OR sender_number_verified_at IS NOT NULL",
            name="ck_notification_channels_fallback",
        ),
    )

    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    status: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(20))
    provider_channel_id: Mapped[str | None] = mapped_column(String(100))
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sender_number: Mapped[str | None] = mapped_column(String(11))
    sender_number_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sms_fallback_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationSettingsOrm(Base):
    """매장의 알림톡 설정(설계 4.2). 연동할 때 기본값으로 생긴다."""

    __tablename__ = "notification_settings"
    __table_args__ = (
        CheckConstraint("reminder_time BETWEEN '08:00' AND '21:00'", name="ck_notification_settings_reminder_time"),
        CheckConstraint(
            "next_visit_after_weeks IS NULL OR next_visit_after_weeks BETWEEN 1 AND 52",
            name="ck_notification_settings_next_visit_after_weeks",
        ),
        CheckConstraint(
            "next_visit_cooldown_days BETWEEN 1 AND 365", name="ck_notification_settings_next_visit_cooldown_days"
        ),
    )

    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    confirm_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    report_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    change_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))   # change·cancel 둘
    next_visit_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    reminder_time: Mapped[time] = mapped_column(Time, server_default=text("'18:00'"))   # 매장 시간대의 벽시계 시각
    next_visit_after_weeks: Mapped[int | None] = mapped_column(SmallInteger)   # NULL = 지난 방문 간격
    next_visit_cooldown_days: Mapped[int] = mapped_column(SmallInteger, server_default=text("30"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationTemplateOrm(Base):
    """매장 채널에 등록한 종류별 템플릿의 심사 상태(설계 4.3). 문안은 코드에 있다(text_version)."""

    __tablename__ = "notification_templates"
    __table_args__ = (
        CheckConstraint(_in("kind", KINDS), name="ck_notification_templates_kind"),
        CheckConstraint(_in("status", TEMPLATE_STATUSES), name="ck_notification_templates_status"),
        UniqueConstraint("shop_id", "kind", name="uq_notification_templates_shop_kind"),
        # 승인 전 판 — 둘은 함께 있거나 함께 없다(0013).
        CheckConstraint(
            "(pending_text_version IS NULL) = (pending_provider_template_id IS NULL)",
            name="ck_notification_templates_pending_pair",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(20))
    text_version: Mapped[int] = mapped_column(SmallInteger)
    provider_template_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    rejected_reason: Mapped[str | None] = mapped_column(String(500))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_text_version: Mapped[int | None] = mapped_column(SmallInteger)
    pending_provider_template_id: Mapped[str | None] = mapped_column(String(100))


class NotificationMessageOrm(Base):
    """알림 줄 하나 — 큐이자 발송 기록(설계 4.4). 전화번호·이름은 저장하지 않는다. variables 에는 알림장 주소가 든다."""

    __tablename__ = "notification_messages"
    __table_args__ = (
        CheckConstraint(_in("kind", KINDS), name="ck_notification_messages_kind"),
        CheckConstraint(_in("status", STATUSES), name="ck_notification_messages_status"),
        CheckConstraint(
            "channel_used IS NULL OR " + _in("channel_used", CHANNELS_USED), name="ck_notification_messages_channel_used"
        ),
        CheckConstraint(
            "error_kind IS NULL OR " + _in("error_kind", ERROR_KINDS), name="ck_notification_messages_error_kind"
        ),
        CheckConstraint(
            "canceled_reason IS NULL OR " + _in("canceled_reason", CANCEL_REASONS),
            name="ck_notification_messages_canceled_reason",
        ),
        CheckConstraint("canceled_reason IS NULL OR status = 'canceled'", name="ck_notification_messages_canceled"),
        # 같은 방문·같은 종류의 대기 줄은 하나(N5).
        Index(
            "uq_notification_messages_pending", "visit_id", "kind", unique=True,
            postgresql_where=text(_PENDING_IN),
        ),
        Index("ix_notification_messages_due", "status", "scheduled_at"),          # 디스패처가 집는 질의
        Index("ix_notification_messages_cooldown", "customer_id", "kind", "sent_at"),
        Index("ix_notification_messages_shop_day", "shop_id", "created_at"),       # 하루 상한
        Index("ix_notification_messages_visit", "visit_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 다른 스포크(tenancy·visit·customer)의 ID — 외래 키 없이 색인만.
    shop_id: Mapped[int] = mapped_column(BigInteger)
    visit_id: Mapped[int] = mapped_column(BigInteger)
    customer_id: Mapped[int] = mapped_column(BigInteger)
    pet_id: Mapped[int | None] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(20))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default=text("'scheduled'"))
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    channel_used: Mapped[str | None] = mapped_column(String(10))
    provider_message_id: Mapped[str | None] = mapped_column(String(100))
    error_code: Mapped[str | None] = mapped_column(String(20))
    error_kind: Mapped[str | None] = mapped_column(String(10))
    variables: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    requested_by_member_id: Mapped[int | None] = mapped_column(BigInteger)   # tenancy 의 멤버 ID
    canceled_reason: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
