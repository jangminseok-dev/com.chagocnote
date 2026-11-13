"""매출 — 매장의 월 목표 금액 칸(visit_shop_settings.sales_monthly_goal)

매장마다 월 목표 하나를 둔다(설계 ⑧ 3.5). 알림장 설정처럼 일정 설정 행의 칸이다 — NULL 이면 목표 없음.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_TABLE, _CHECK = "visit_shop_settings", "ck_visit_shop_settings_sales_goal"


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column("sales_monthly_goal", sa.Integer))
    op.create_check_constraint(
        _CHECK, _TABLE, "sales_monthly_goal IS NULL OR sales_monthly_goal BETWEEN 1 AND 100000000"
    )


def downgrade() -> None:
    op.drop_constraint(_CHECK, _TABLE, type_="check")
    op.drop_column(_TABLE, "sales_monthly_goal")
