"""보호자 회원 — 보호자 계정과 매장의 고객 카드를 잇는 연결(guardian_links)

고객 카드 하나에 살아 있는 연결은 하나다(부분 유일 색인). 끝난 줄은 남긴다. 전화번호·이름을 저장하지 않는다.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-13
"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

# 값 목록은 글자로 적는다 — tests/integration/test_guardian_schema.py 가 도메인 튜플과 같은 순서인지 실제 DB 로 본다.
_VERIFIED_BY = "('report_link')"
_ENDED_BY = "('guardian', 'shop', 'withdrawn', 'anonymized')"


def upgrade() -> None:
    op.create_table(
        "guardian_links",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.BigInteger, nullable=False),
        sa.Column("verified_by", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("ended_by", sa.String(20)),
        sa.CheckConstraint("verified_by IN " + _VERIFIED_BY, name="ck_guardian_links_verified_by"),
        sa.CheckConstraint("ended_by IS NULL OR ended_by IN " + _ENDED_BY, name="ck_guardian_links_ended_by"),
        sa.CheckConstraint("(ended_at IS NULL) = (ended_by IS NULL)", name="ck_guardian_links_ended"),
    )
    op.create_index(
        "uq_guardian_links_live", "guardian_links", ["shop_id", "customer_id"], unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.create_index(
        "ix_guardian_links_user", "guardian_links", ["user_id"], postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_guardian_links_user", table_name="guardian_links")
    op.drop_index("uq_guardian_links_live", table_name="guardian_links")
    op.drop_table("guardian_links")
