"""⑭ 반복 예약의 묶음.

visit_series: 한꺼번에 잡은 예약들의 묶음 — 보호자와 간격(1~12주)만 남긴다(보여 주려고만, 뒤에서 예약을 만들지 않는다).
visits.series_id: 그 방문이 든 묶음(없으면 따로 잡은 예약).

Revision ID: 0026
Revises: 0025
"""
from alembic import op
import sqlalchemy as sa

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visit_series",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.BigInteger, nullable=False),
        sa.Column("interval_weeks", sa.SmallInteger, nullable=False),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("interval_weeks BETWEEN 1 AND 12", name="ck_visit_series_interval_weeks"),
    )
    op.create_index("ix_visit_series_shop_customer", "visit_series", ["shop_id", "customer_id"])
    op.add_column("visits", sa.Column("series_id", sa.BigInteger))
    op.create_foreign_key("fk_visits_series_id", "visits", "visit_series", ["series_id"], ["id"])
    op.create_index("ix_visits_series", "visits", ["series_id"], postgresql_where=sa.text("series_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("ix_visits_series", table_name="visits")
    op.drop_constraint("fk_visits_series_id", "visits", type_="foreignkey")
    op.drop_column("visits", "series_id")
    op.drop_index("ix_visit_series_shop_customer", table_name="visit_series")
    op.drop_table("visit_series")
