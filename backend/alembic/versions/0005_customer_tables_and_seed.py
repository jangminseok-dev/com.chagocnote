"""고객·반려동물·질병·검색 표 + 질병 종류 시드 + pg_trgm

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-22
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),  # tenancy 의 매장 ID — 스포크를 넘는 외래 키는 걸지 않는다
        sa.Column("name", sa.String(50)),
        sa.Column("phone", sa.String(11)),
        sa.Column("phone_alt", sa.String(11)),
        sa.Column("marketing_consent", sa.Boolean, nullable=False),
        sa.Column("marketing_consent_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("memo", sa.String(500)),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "deleted_at IS NOT NULL OR (name IS NOT NULL AND phone IS NOT NULL)",
            name="ck_customers_alive_has_name_phone",
        ),
    )
    op.create_index("ix_customers_shop_id", "customers", ["shop_id"])
    op.create_index(
        "uq_customers_shop_phone_active", "customers", ["shop_id", "phone"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "pets",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("customer_id", sa.BigInteger, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("name", sa.String(50)),
        sa.Column("species", sa.String(10), nullable=False),
        sa.Column("breed", sa.String(50), nullable=False),
        sa.Column("sex", sa.String(10), nullable=False),
        sa.Column("neutered", sa.Boolean, nullable=False),
        sa.Column("birth_date", sa.Date),
        sa.Column("birth_year", sa.SmallInteger),
        sa.Column("weight_kg", sa.Numeric(4, 1), nullable=False),
        sa.Column("no_known_conditions", sa.Boolean, nullable=False),
        sa.Column("memo", sa.String(500)),
        sa.Column("passed_away_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("species IN ('dog', 'cat')", name="ck_pets_species"),
        sa.CheckConstraint("sex IN ('female', 'male')", name="ck_pets_sex"),
        sa.CheckConstraint("weight_kg > 0", name="ck_pets_weight_positive"),
        sa.CheckConstraint("birth_date IS NULL OR birth_year IS NULL", name="ck_pets_one_birth_field"),
    )
    op.create_index("ix_pets_customer_id", "pets", ["customer_id"])

    condition_types = op.create_table(
        "pet_condition_types",
        sa.Column("code", sa.String(30), primary_key=True),
        sa.Column("label", sa.String(30), nullable=False),
        sa.Column("sort_order", sa.SmallInteger, nullable=False),
    )

    op.create_table(
        "pet_conditions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("pet_id", sa.BigInteger, sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type_code", sa.String(30), sa.ForeignKey("pet_condition_types.code"), nullable=False),
        sa.Column("custom_label", sa.String(30)),
        sa.Column("note", sa.String(100)),
        sa.CheckConstraint(
            "(type_code = 'other') = (custom_label IS NOT NULL)", name="ck_pet_conditions_other_label"
        ),
    )
    op.create_index("ix_pet_conditions_pet_id", "pet_conditions", ["pet_id"])
    op.create_index(
        "uq_pet_conditions_pet_type", "pet_conditions", ["pet_id", "type_code"],
        unique=True, postgresql_where=sa.text("type_code <> 'other'"),
    )

    op.create_table(
        "customer_search_entries",
        sa.Column("customer_id", sa.BigInteger, sa.ForeignKey("customers.id"), primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("terms", sa.Text, nullable=False),
        sa.Column("phone_last4", sa.String(4), nullable=False),
        sa.Column("sort_name", sa.String(50), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_customer_search_entries_terms_trgm", "customer_search_entries", ["terms"],
        postgresql_using="gin", postgresql_ops={"terms": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_customer_search_entries_shop_activity", "customer_search_entries",
        ["shop_id", "last_activity_at"],
    )
    op.create_index(
        "ix_customer_search_entries_shop_sort_name", "customer_search_entries",
        ["shop_id", "sort_name"],
    )

    op.bulk_insert(
        condition_types,
        [
            {"code": "patella_luxation", "label": "슬개골 탈구", "sort_order": 1},
            {"code": "heart_disease", "label": "심장 질환", "sort_order": 2},
            {"code": "skin_disease", "label": "피부병", "sort_order": 3},
            {"code": "arthritis", "label": "관절염", "sort_order": 4},
            {"code": "allergy", "label": "알레르기", "sort_order": 5},
            {"code": "ear_disease", "label": "귀 질환", "sort_order": 6},
            {"code": "disc_disease", "label": "디스크", "sort_order": 7},
            {"code": "seizure", "label": "발작·뇌전증", "sort_order": 8},
            {"code": "diabetes", "label": "당뇨", "sort_order": 9},
            {"code": "other", "label": "기타", "sort_order": 10},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_customer_search_entries_shop_sort_name", table_name="customer_search_entries")
    op.drop_index("ix_customer_search_entries_shop_activity", table_name="customer_search_entries")
    op.drop_index("ix_customer_search_entries_terms_trgm", table_name="customer_search_entries")
    op.drop_table("customer_search_entries")
    op.drop_index("uq_pet_conditions_pet_type", table_name="pet_conditions")
    op.drop_index("ix_pet_conditions_pet_id", table_name="pet_conditions")
    op.drop_table("pet_conditions")
    op.drop_table("pet_condition_types")
    op.drop_index("ix_pets_customer_id", table_name="pets")
    op.drop_table("pets")
    op.drop_index("uq_customers_shop_phone_active", table_name="customers")
    op.drop_index("ix_customers_shop_id", table_name="customers")
    op.drop_table("customers")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
