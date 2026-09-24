"""미용 기록 — 기록·실제 메뉴와 금액·붙은 사진영상

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _now(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "visit_records",
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("weight_kg", sa.Numeric(4, 1)),
        sa.Column("care_note", sa.String(1000)),
        sa.Column("internal_note", sa.String(1000)),
        sa.Column("payment_method", sa.String(10)),
        sa.Column("total_amount", sa.Integer),
        sa.Column("version", sa.Integer, server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("updated_by_member_id", sa.BigInteger, nullable=False),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint("weight_kg IS NULL OR weight_kg > 0", name="ck_visit_records_weight"),
        sa.CheckConstraint(
            "payment_method IS NULL OR payment_method IN ('card', 'cash', 'transfer')",
            name="ck_visit_records_payment_method",
        ),
        sa.CheckConstraint(
            "total_amount IS NULL OR total_amount BETWEEN 0 AND 100000000", name="ck_visit_records_total_amount"
        ),
        sa.CheckConstraint("version >= 1", name="ck_visit_records_version"),
    )
    op.create_table(
        "visit_record_items",
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visit_records.visit_id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("menu_id", sa.BigInteger, sa.ForeignKey("service_menus.id"), primary_key=True),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.CheckConstraint("amount BETWEEN 0 AND 100000000", name="ck_visit_record_items_amount"),
    )
    op.create_table(
        "visit_record_media",
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visit_records.visit_id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("media_id", sa.BigInteger, primary_key=True, autoincrement=False),   # media 의 ID — 외래 키 없음
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("phase", sa.String(10), nullable=False),
        sa.Column("sort_order", sa.SmallInteger, nullable=False),
        sa.CheckConstraint("kind IN ('photo', 'video')", name="ck_visit_record_media_kind"),
        sa.CheckConstraint("phase IN ('before', 'after')", name="ck_visit_record_media_phase"),
        sa.CheckConstraint("sort_order BETWEEN 0 AND 99", name="ck_visit_record_media_sort_order"),
        sa.UniqueConstraint("media_id", name="visit_record_media_media_id_key"),
    )
    op.create_index(
        "uq_visit_record_media_order", "visit_record_media", ["visit_id", "phase", "sort_order"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_visit_record_media_order", table_name="visit_record_media")
    op.drop_table("visit_record_media")
    op.drop_table("visit_record_items")
    op.drop_table("visit_records")
