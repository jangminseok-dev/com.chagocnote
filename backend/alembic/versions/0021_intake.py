"""첫 방문 문진표 — ⑪-C

customer_forms.intake_pet_id: 이미 있는 아이의 정보를 다시 받는 문진표가 가리키는 아이. 그런 요청은 아이마다 하나만 산다.
shop_form_settings 의 두 칸: 확인하지 않은 답을 지우는 날 수, 매장이 끈 칸.
shop_intake_questions: 매장이 더한 질문. 지운 질문의 행은 남긴다(받은 답이 가리킨다).
intake_answers 와 그 아래 표: 받은 문진표. 등록·반영·지우기·기한에서 행을 지운다 — 고객·반려동물 표를 건드리지 않는다.

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-16
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customer_forms", sa.Column("intake_pet_id", sa.BigInteger, sa.ForeignKey("pets.id")))
    op.create_index(
        "uq_customer_forms_live_intake_pet", "customer_forms", ["intake_pet_id"], unique=True,
        postgresql_where=sa.text("kind = 'intake' AND revoked_at IS NULL AND submitted_at IS NULL"),
    )
    op.add_column("shop_form_settings", sa.Column(
        "intake_keep_days", sa.SmallInteger, nullable=False, server_default="30"))
    op.add_column("shop_form_settings", sa.Column(
        "intake_hidden", postgresql.ARRAY(sa.String(20)), nullable=False, server_default="{}"))
    op.create_check_constraint(
        "ck_shop_form_settings_intake_keep_days", "shop_form_settings", "intake_keep_days BETWEEN 7 AND 90")
    op.create_table(
        "shop_intake_questions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("position", sa.SmallInteger, nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("required", sa.Boolean, nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_shop_intake_questions_shop_id", "shop_intake_questions", ["shop_id"])
    op.create_table(
        "intake_answers",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("form_id", sa.BigInteger, sa.ForeignKey("customer_forms.id"), nullable=False),
        sa.Column("matched_customer_id", sa.BigInteger, sa.ForeignKey("customers.id")),
        sa.Column("guardian_name", sa.String(50)),
        sa.Column("guardian_phone", sa.String(20)),
        sa.Column("pet_name", sa.String(50)),
        sa.Column("species", sa.String(10)),
        sa.Column("breed", sa.String(50)),
        sa.Column("sex", sa.String(10)),
        sa.Column("neutered", sa.Boolean),
        sa.Column("birth_date", sa.Date),
        sa.Column("birth_year", sa.SmallInteger),
        sa.Column("birth_unknown", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("weight_kg", sa.Numeric(4, 1)),
        sa.Column("no_known_conditions", sa.Boolean),
        sa.Column("dislikes", sa.String(200)),
        sa.Column("style", sa.String(200)),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_intake_answers_shop_id", "intake_answers", ["shop_id"])
    op.create_index("ix_intake_answers_form_id", "intake_answers", ["form_id"])
    op.create_table(
        "intake_answer_conditions",
        sa.Column("answer_id", sa.BigInteger, sa.ForeignKey("intake_answers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.SmallInteger, primary_key=True),
        sa.Column("type_code", sa.String(30), nullable=False),
        sa.Column("custom_label", sa.String(30)),
        sa.Column("note", sa.String(100)),
    )
    op.create_table(
        "intake_answer_extras",
        sa.Column("answer_id", sa.BigInteger, sa.ForeignKey("intake_answers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("question_id", sa.BigInteger, sa.ForeignKey("shop_intake_questions.id"), primary_key=True),
        sa.Column("body", sa.String(200), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("intake_answer_extras")
    op.drop_table("intake_answer_conditions")
    op.drop_table("intake_answers")
    op.drop_table("shop_intake_questions")
    op.drop_constraint("ck_shop_form_settings_intake_keep_days", "shop_form_settings")
    op.drop_column("shop_form_settings", "intake_hidden")
    op.drop_column("shop_form_settings", "intake_keep_days")
    op.drop_index("uq_customer_forms_live_intake_pet", table_name="customer_forms")
    op.drop_column("customer_forms", "intake_pet_id")
