"""알림톡 — 매장 채널(notification_channels), 설정, 템플릿 심사 상태, 메시지 큐이자 발송 기록

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

# 상태 목록은 글자로 적는다 — tests/integration/test_notification_schema.py 가 도메인 튜플과 같은 순서인지 실제 DB 로 본다.
_KINDS = "('confirm', 'reminder', 'report', 'change', 'cancel', 'next_visit')"
_STATUSES = "('scheduled', 'sending', 'accepted', 'sent', 'fallback_sent', 'failed', 'canceled')"
_CANCEL_REASONS = (
    "('rescheduled', 'visit_canceled', 'no_show', 'setting_off', 'channel_unlinked', 'shop_closed', "
    "'template_rejected', 'report_revoked', 'too_late', 'anonymized', 'has_upcoming', 'cooldown', "
    "'no_consent', 'bad_phone')"
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # 매장당 한 줄. shop_id 는 tenancy 의 ID — 스포크를 넘는 외래 키는 걸지 않는다.
    op.create_table(
        "notification_channels",
        sa.Column("shop_id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_channel_id", sa.String(100)),
        sa.Column("linked_at", sa.DateTime(timezone=True)),
        sa.Column("unlinked_at", sa.DateTime(timezone=True)),
        sa.Column("sender_number", sa.String(11)),
        sa.Column("sender_number_verified_at", sa.DateTime(timezone=True)),
        sa.Column("sms_fallback_enabled", sa.Boolean, server_default=sa.text("false"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('token_requested', 'linked', 'unlinked')", name="ck_notification_channels_status"
        ),
        # 문자 대체는 발신번호 인증을 마쳐야 켤 수 있다(N11).
        sa.CheckConstraint(
            "NOT sms_fallback_enabled OR sender_number_verified_at IS NOT NULL",
            name="ck_notification_channels_fallback",
        ),
    )
    op.create_table(
        "notification_settings",
        sa.Column("shop_id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("confirm_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("reminder_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("report_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("change_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("next_visit_enabled", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("reminder_time", sa.Time, server_default=sa.text("'18:00'"), nullable=False),
        sa.Column("next_visit_after_weeks", sa.SmallInteger),
        sa.Column("next_visit_cooldown_days", sa.SmallInteger, server_default=sa.text("30"), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "reminder_time BETWEEN '08:00' AND '21:00'", name="ck_notification_settings_reminder_time"
        ),
        sa.CheckConstraint(
            "next_visit_after_weeks IS NULL OR next_visit_after_weeks BETWEEN 1 AND 52",
            name="ck_notification_settings_next_visit_after_weeks",
        ),
        sa.CheckConstraint(
            "next_visit_cooldown_days BETWEEN 1 AND 365", name="ck_notification_settings_next_visit_cooldown_days"
        ),
    )
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("text_version", sa.SmallInteger, nullable=False),
        sa.Column("provider_template_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rejected_reason", sa.String(500)),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN " + _KINDS, name="ck_notification_templates_kind"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_notification_templates_status"
        ),
        sa.UniqueConstraint("shop_id", "kind", name="uq_notification_templates_shop_kind"),
    )
    # 큐이자 발송 기록. 전화번호·이름은 저장하지 않는다(설계 4.5). variables 에는 알림장 주소가 든다 — 응답·로그에 싣지 않는다.
    op.create_table(
        "notification_messages",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("visit_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.BigInteger, nullable=False),
        sa.Column("pet_id", sa.BigInteger),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'scheduled'"), nullable=False),
        sa.Column("attempts", sa.SmallInteger, server_default=sa.text("0"), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("channel_used", sa.String(10)),
        sa.Column("provider_message_id", sa.String(100)),
        sa.Column("error_code", sa.String(20)),
        sa.Column("error_kind", sa.String(10)),
        sa.Column("variables", postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("requested_by_member_id", sa.BigInteger),
        sa.Column("canceled_reason", sa.String(20)),
        *_timestamps(),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN " + _KINDS, name="ck_notification_messages_kind"),
        sa.CheckConstraint("status IN " + _STATUSES, name="ck_notification_messages_status"),
        sa.CheckConstraint(
            "channel_used IS NULL OR channel_used IN ('alimtalk', 'sms', 'lms')",
            name="ck_notification_messages_channel_used",
        ),
        sa.CheckConstraint(
            "error_kind IS NULL OR error_kind IN ('transient', 'permanent')",
            name="ck_notification_messages_error_kind",
        ),
        sa.CheckConstraint(
            "canceled_reason IS NULL OR canceled_reason IN " + _CANCEL_REASONS,
            name="ck_notification_messages_canceled_reason",
        ),
        sa.CheckConstraint(
            "canceled_reason IS NULL OR status = 'canceled'", name="ck_notification_messages_canceled"
        ),
    )
    # 같은 방문·같은 종류의 대기 줄은 하나(N5). 디스패처가 집는 질의, 쿨다운, 하루 상한, 방문별 내역의 색인.
    op.create_index(
        "uq_notification_messages_pending", "notification_messages", ["visit_id", "kind"], unique=True,
        postgresql_where=sa.text("status IN ('scheduled', 'sending')"),
    )
    op.create_index("ix_notification_messages_due", "notification_messages", ["status", "scheduled_at"])
    op.create_index("ix_notification_messages_cooldown", "notification_messages", ["customer_id", "kind", "sent_at"])
    op.create_index("ix_notification_messages_shop_day", "notification_messages", ["shop_id", "created_at"])
    op.create_index("ix_notification_messages_visit", "notification_messages", ["visit_id"])


def downgrade() -> None:
    op.drop_table("notification_messages")
    op.drop_table("notification_templates")
    op.drop_table("notification_settings")
    op.drop_table("notification_channels")
