"""서류 설정과 매장이 고친 동의서 글 — ⑪-B

shop_form_settings: 매장이 바꾼 기준값(링크 기간·노령 나이·동의 기한)과 보호자에게 보내는 글의 템플릿.
행이 없으면 기본값이다. 글 칸이 비어 있으면(NULL) 기본 글이다.
shop_consent_texts: 매장이 고친 동의서 토막의 글. 쌓기만 한다 — 옛 서명을 그 글자로 다시 보여야 한다.
body 가 NULL 인 판은 "기본 글로 되돌렸다"는 뜻이다.

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_form_settings",
        sa.Column("shop_id", sa.BigInteger, primary_key=True),
        sa.Column("link_days", sa.SmallInteger, nullable=False),
        sa.Column("senior_age", sa.SmallInteger, nullable=False),
        sa.Column("consent_days", sa.SmallInteger, nullable=False),
        sa.Column("reservation_text", sa.String(500)),
        sa.Column("consent_text", sa.String(500)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("link_days BETWEEN 1 AND 30", name="ck_shop_form_settings_link_days"),
        sa.CheckConstraint("senior_age BETWEEN 5 AND 20", name="ck_shop_form_settings_senior_age"),
        sa.CheckConstraint("consent_days BETWEEN 30 AND 1095", name="ck_shop_form_settings_consent_days"),
    )
    op.create_table(
        "shop_consent_texts",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("part", sa.String(10), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("body", sa.String(2000)),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("part IN ('basic', 'senior', 'condition')", name="ck_shop_consent_texts_part"),
        sa.UniqueConstraint("shop_id", "part", "version", name="uq_shop_consent_texts_shop_part_version"),
    )


def downgrade() -> None:
    op.drop_table("shop_consent_texts")
    op.drop_table("shop_form_settings")
