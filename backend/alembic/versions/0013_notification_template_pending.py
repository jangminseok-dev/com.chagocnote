"""알림톡 — 템플릿에 승인 전 판 칸 둘(pending_text_version·pending_provider_template_id)을 더한다

승인된 종류를 새 판으로 재등록해도 심사가 끝날 때까지 옛 판으로 계속 보내려고, 새 판을 본 칸에 덮지 않고 여기에 둔다
(설계 2026-11-10 3.2). 둘은 함께 있거나 함께 없다.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_TABLE, _PAIR = "notification_templates", "ck_notification_templates_pending_pair"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("pending_text_version", sa.SmallInteger))
    op.add_column(_TABLE, sa.Column("pending_provider_template_id", sa.String(100)))
    op.create_check_constraint(
        _PAIR, _TABLE, "(pending_text_version IS NULL) = (pending_provider_template_id IS NULL)"
    )


def downgrade() -> None:
    op.drop_constraint(_PAIR, _TABLE, type_="check")
    op.drop_column(_TABLE, "pending_provider_template_id")
    op.drop_column(_TABLE, "pending_text_version")
