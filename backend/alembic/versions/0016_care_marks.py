"""미용 동의 받은 날(pets)과 주의 표시(customers) — ③-B

둘 다 "지금의 것 하나"라 새 표가 아니라 칸이다(설계 ③-B 4.1). 주의 칸 넷은 함께 있거나 함께 없고,
동의 칸 둘도 그렇다. 기한이 지난 주의는 지우지 않고 읽을 때 거른다.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

_CONSENT_CHECK = "ck_pets_grooming_consent_all_or_none"
_CAUTION_CHECK = "ck_customers_caution_all_or_none"


def upgrade() -> None:
    op.add_column("pets", sa.Column("grooming_consent_on", sa.Date))
    op.add_column("pets", sa.Column("grooming_consent_by_member_id", sa.BigInteger))
    op.create_check_constraint(
        _CONSENT_CHECK, "pets",
        "(grooming_consent_on IS NULL) = (grooming_consent_by_member_id IS NULL)",
    )
    op.add_column("customers", sa.Column("caution_reason", sa.String(100)))
    op.add_column("customers", sa.Column("caution_until", sa.Date))
    op.add_column("customers", sa.Column("caution_set_at", sa.DateTime(timezone=True)))
    op.add_column("customers", sa.Column("caution_set_by_member_id", sa.BigInteger))
    op.create_check_constraint(
        _CAUTION_CHECK, "customers",
        "(caution_reason IS NULL) = (caution_until IS NULL) "
        "AND (caution_reason IS NULL) = (caution_set_at IS NULL) "
        "AND (caution_reason IS NULL) = (caution_set_by_member_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(_CAUTION_CHECK, "customers", type_="check")
    for column in ("caution_set_by_member_id", "caution_set_at", "caution_until", "caution_reason"):
        op.drop_column("customers", column)
    op.drop_constraint(_CONSENT_CHECK, "pets", type_="check")
    op.drop_column("pets", "grooming_consent_by_member_id")
    op.drop_column("pets", "grooming_consent_on")
