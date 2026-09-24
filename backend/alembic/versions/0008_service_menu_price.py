"""메뉴 정가

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_menus", sa.Column("price", sa.Integer))   # NULL 이면 가격 미정
    op.create_check_constraint(
        "ck_service_menus_price", "service_menus", "price IS NULL OR price BETWEEN 0 AND 100000000"
    )


def downgrade() -> None:
    op.drop_constraint("ck_service_menus_price", "service_menus", type_="check")
    op.drop_column("service_menus", "price")
