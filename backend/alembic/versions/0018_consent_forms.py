"""서류 요청과 동의서 서명 — ⑪-A

보호자가 로그인 없이 여는 서류 링크(customer_forms)와 서명 한 번의 기록(consent_signatures 와 그 아래 표).
서명은 읽은 토막과 그 글의 판, 그때 보인 아이 이름·지병 이름의 사본을 남긴다 — 뒤에 지병이 늘면 바뀐 토막만 다시 받는다.
pets.grooming_consent_signature_id 는 받은 날을 찍은 서명이다(손으로 적은 동의면 비어 있다).

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-16
"""
import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

_SIGNATURE_CHECK = "ck_pets_grooming_consent_signature_needs_day"


def upgrade() -> None:
    op.create_table(
        "customer_forms",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("public_id", sa.LargeBinary, nullable=False),
        sa.Column("customer_id", sa.BigInteger, sa.ForeignKey("customers.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('consent', 'intake')", name="ck_customer_forms_kind"),
        sa.CheckConstraint("octet_length(public_id) = 16", name="ck_customer_forms_public_id_length"),
        sa.UniqueConstraint("public_id", name="uq_customer_forms_public_id"),
    )
    op.create_index("ix_customer_forms_shop_customer", "customer_forms", ["shop_id", "customer_id"])
    op.create_table(
        "customer_form_pets",
        sa.Column("form_id", sa.BigInteger, sa.ForeignKey("customer_forms.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("pet_id", sa.BigInteger, sa.ForeignKey("pets.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_customer_form_pets_pet_id", "customer_form_pets", ["pet_id"])
    op.create_table(
        "consent_signatures",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.BigInteger, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("form_id", sa.BigInteger, sa.ForeignKey("customer_forms.id")),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("signer_name", sa.String(50), nullable=False),
        sa.Column("signature_png", sa.LargeBinary, nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("by_member_id", sa.BigInteger, nullable=False),
        sa.CheckConstraint("channel IN ('link', 'in_shop')", name="ck_consent_signatures_channel"),
        sa.CheckConstraint("octet_length(signature_png) <= 65536", name="ck_consent_signatures_png_size"),
        sa.CheckConstraint("(channel = 'link') = (form_id IS NOT NULL)", name="ck_consent_signatures_link_has_form"),
        sa.UniqueConstraint("form_id", name="uq_consent_signatures_form_id"),
    )
    op.create_index("ix_consent_signatures_shop_customer", "consent_signatures", ["shop_id", "customer_id"])
    op.create_table(
        "consent_signature_pets",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("signature_id", sa.BigInteger, sa.ForeignKey("consent_signatures.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("pet_id", sa.BigInteger, sa.ForeignKey("pets.id")),
        sa.Column("shown_pet_name", sa.String(50), nullable=False),
    )
    op.create_index("ix_consent_signature_pets_signature_id", "consent_signature_pets", ["signature_id"])
    op.create_index("ix_consent_signature_pets_pet_id", "consent_signature_pets", ["pet_id"])
    op.create_table(
        "consent_signature_parts",
        sa.Column("signature_pet_id", sa.BigInteger,
                  sa.ForeignKey("consent_signature_pets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("part", sa.String(10), primary_key=True),
        sa.Column("text_source", sa.String(10), nullable=False),
        sa.Column("text_version", sa.Integer, nullable=False),
        sa.CheckConstraint("part IN ('basic', 'senior', 'condition')", name="ck_consent_signature_parts_part"),
        sa.CheckConstraint("text_source IN ('default', 'shop')", name="ck_consent_signature_parts_source"),
    )
    op.create_table(
        "consent_signature_conditions",
        sa.Column("signature_pet_id", sa.BigInteger,
                  sa.ForeignKey("consent_signature_pets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.SmallInteger, primary_key=True),
        sa.Column("label", sa.String(50), nullable=False),
    )
    op.add_column("pets", sa.Column("grooming_consent_signature_id", sa.BigInteger))
    op.create_check_constraint(
        _SIGNATURE_CHECK, "pets",
        "grooming_consent_signature_id IS NULL OR grooming_consent_on IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(_SIGNATURE_CHECK, "pets", type_="check")
    op.drop_column("pets", "grooming_consent_signature_id")
    for table in ("consent_signature_conditions", "consent_signature_parts", "consent_signature_pets",
                  "consent_signatures", "customer_form_pets", "customer_forms"):
        op.drop_table(table)
