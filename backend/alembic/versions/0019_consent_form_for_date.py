"""동의서 요청의 기준일 — ⑪-A

예약 날에 유효한 동의를 지금 받으려면 문서를 그날로 조립해야 한다(그날 기한이 지나는지, 그날 노령인지).
링크는 뒤에 열리므로 보낼 때의 기준일을 요청에 적어 둔다. 없으면 여는 날이다.

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customer_forms", sa.Column("for_date", sa.Date))


def downgrade() -> None:
    op.drop_column("customer_forms", "for_date")
