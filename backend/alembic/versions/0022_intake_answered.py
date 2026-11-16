"""문진표 링크로 받은 답의 수 — ⑪-C

한 링크에 아이는 열 마리까지다. 답은 등록하거나 지우면 행이 없어지므로, 받은 수를 요청 행에 따로 적어 둔다 —
답을 지워도 한도가 다시 열리지 않는다.

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customer_forms", sa.Column(
        "intake_answered", sa.SmallInteger, nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("customer_forms", "intake_answered")
