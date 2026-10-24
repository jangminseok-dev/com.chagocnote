"""알림톡 — 취소 이유에 reverted(완료를 되돌림)·passed_away(무지개다리를 건넌 아이)를 더한다

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-24
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_TABLE, _NAME = "notification_messages", "ck_notification_messages_canceled_reason"
_BEFORE = (
    "('rescheduled', 'visit_canceled', 'no_show', 'setting_off', 'channel_unlinked', 'shop_closed', "
    "'template_rejected', 'report_revoked', 'too_late', 'anonymized', 'has_upcoming', 'cooldown', "
    "'no_consent', 'bad_phone')"
)
_AFTER = _BEFORE[:-1] + ", 'reverted', 'passed_away')"


def upgrade() -> None:
    op.drop_constraint(_NAME, _TABLE, type_="check")
    op.create_check_constraint(_NAME, _TABLE, "canceled_reason IS NULL OR canceled_reason IN " + _AFTER)


def downgrade() -> None:
    op.drop_constraint(_NAME, _TABLE, type_="check")
    op.create_check_constraint(_NAME, _TABLE, "canceled_reason IS NULL OR canceled_reason IN " + _BEFORE)
