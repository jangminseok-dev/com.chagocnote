"""문진표 끝의 동의서(⑪-C1b) — 아이 없이 맡아 두는 서명, 서류 설정의 `모든 아이에게`.

consent_signatures: 맡아 둔 서명은 고객이 없고(customer_id NULL) 받은 문진표에 매달린다(intake_answer_id).
답이 지워지면 함께 지워진다(CASCADE) — 등록·반영은 답을 지우기 전에 서명을 떼어 낸다(intake_answer_id 를 비운다).
받은 길에 intake(문진표에서 서명)가 는다. 고객도 답도 없는 서명은 없다.
shop_form_settings.intake_consent_all: 첫 방문 문진표에서 모든 아이에게 동의서를 받는다(기본 꺼짐).

Revision ID: 0023
Revises: 0022
"""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

_CHANNEL = "ck_consent_signatures_channel"
_OWNER = "ck_consent_signatures_owner"


def upgrade() -> None:
    op.add_column("shop_form_settings", sa.Column(
        "intake_consent_all", sa.Boolean, nullable=False, server_default=sa.false()))
    op.alter_column("consent_signatures", "customer_id", existing_type=sa.BigInteger, nullable=True)
    op.add_column("consent_signatures", sa.Column(
        "intake_answer_id", sa.BigInteger, sa.ForeignKey("intake_answers.id", ondelete="CASCADE")))
    op.create_index("ix_consent_signatures_intake_answer_id", "consent_signatures", ["intake_answer_id"])
    op.drop_constraint(_CHANNEL, "consent_signatures", type_="check")
    op.create_check_constraint(_CHANNEL, "consent_signatures", "channel IN ('link', 'in_shop', 'intake')")
    op.create_check_constraint(_OWNER, "consent_signatures", "customer_id IS NOT NULL OR intake_answer_id IS NOT NULL")


def downgrade() -> None:
    op.execute("DELETE FROM consent_signatures WHERE customer_id IS NULL")
    op.drop_constraint(_OWNER, "consent_signatures", type_="check")
    op.drop_constraint(_CHANNEL, "consent_signatures", type_="check")
    op.execute("DELETE FROM consent_signatures WHERE channel = 'intake'")
    op.create_check_constraint(_CHANNEL, "consent_signatures", "channel IN ('link', 'in_shop')")
    op.drop_index("ix_consent_signatures_intake_answer_id", "consent_signatures")
    op.drop_column("consent_signatures", "intake_answer_id")
    op.alter_column("consent_signatures", "customer_id", existing_type=sa.BigInteger, nullable=False)
    op.drop_column("shop_form_settings", "intake_consent_all")
