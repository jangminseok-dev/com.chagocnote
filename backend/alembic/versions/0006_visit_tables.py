"""방문·매장 일정·메뉴 표 + 검색 줄의 마지막 방문 시각

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_DURATION_RULE = "BETWEEN 10 AND 600 AND {col} % 10 = 0"


def _now(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "visit_shop_settings",
        sa.Column("shop_id", sa.BigInteger, primary_key=True, autoincrement=False),  # tenancy 의 매장 ID
        sa.Column("opens_at", sa.Time, nullable=False),
        sa.Column("closes_at", sa.Time, nullable=False),
        sa.Column("default_duration_minutes", sa.SmallInteger, nullable=False),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint("opens_at < closes_at", name="ck_visit_shop_settings_hours"),
        sa.CheckConstraint(
            "default_duration_minutes " + _DURATION_RULE.format(col="default_duration_minutes"),
            name="ck_visit_shop_settings_duration",
        ),
    )

    op.create_table(
        "visit_weekly_closures",
        sa.Column("shop_id", sa.BigInteger, sa.ForeignKey("visit_shop_settings.shop_id"), primary_key=True),
        sa.Column("weekday", sa.SmallInteger, primary_key=True, autoincrement=False),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_visit_weekly_closures_weekday"),
    )

    op.create_table(
        "visit_closed_dates",
        sa.Column("shop_id", sa.BigInteger, sa.ForeignKey("visit_shop_settings.shop_id"), primary_key=True),
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("note", sa.String(30)),
    )

    op.create_table(
        "service_menus",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, sa.ForeignKey("visit_shop_settings.shop_id"), nullable=False),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("default_duration_minutes", sa.SmallInteger),
        sa.Column("sort_order", sa.SmallInteger, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        _now("created_at"),
        sa.CheckConstraint(
            "default_duration_minutes IS NULL OR default_duration_minutes "
            + _DURATION_RULE.format(col="default_duration_minutes"),
            name="ck_service_menus_duration",
        ),
    )
    op.create_index("ix_service_menus_shop_id", "service_menus", ["shop_id"])
    op.create_index(
        "uq_service_menus_shop_name_active", "service_menus", ["shop_id", "name"],
        unique=True, postgresql_where=sa.text("archived_at IS NULL"),
    )

    op.create_table(
        "visits",
        sa.Column("id", sa.BigInteger, primary_key=True),
        # 다른 스포크의 ID — 외래 키 없이 색인만(설계 5.3).
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.BigInteger, nullable=False),
        sa.Column("pet_id", sa.BigInteger),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_reason", sa.String(20)),
        sa.Column("memo", sa.String(500)),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("status_changed_by_member_id", sa.BigInteger),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint(
            "status IN ('reserved', 'in_progress', 'completed', 'canceled', 'no_show')",
            name="ck_visits_status",
        ),
        sa.CheckConstraint(
            "duration_minutes " + _DURATION_RULE.format(col="duration_minutes"),
            name="ck_visits_duration",
        ),
        sa.CheckConstraint(
            "cancel_reason IS NULL OR cancel_reason IN ('customer_request', 'shop_reason')",
            name="ck_visits_cancel_reason",
        ),
        sa.CheckConstraint(
            "(status = 'canceled') = (canceled_at IS NOT NULL) "
            "AND (status = 'canceled') = (cancel_reason IS NOT NULL)",
            name="ck_visits_canceled_fields",
        ),
        sa.CheckConstraint(
            "(status = 'completed') = (completed_at IS NOT NULL)", name="ck_visits_completed_at"
        ),
        sa.CheckConstraint(
            "(status IN ('in_progress', 'completed')) = (started_at IS NOT NULL)",
            name="ck_visits_started_at",
        ),
    )
    op.create_index(
        "uq_visits_pet_start_active", "visits", ["pet_id", "starts_at"], unique=True,
        postgresql_where=sa.text("pet_id IS NOT NULL AND status IN ('reserved', 'in_progress')"),
    )
    op.create_index(
        "uq_visits_customer_start_active", "visits", ["customer_id", "starts_at"], unique=True,
        postgresql_where=sa.text("pet_id IS NULL AND status IN ('reserved', 'in_progress')"),
    )
    op.create_index("ix_visits_shop_starts_at", "visits", ["shop_id", "starts_at"])
    op.create_index("ix_visits_shop_customer", "visits", ["shop_id", "customer_id"])
    op.create_index("ix_visits_shop_pet", "visits", ["shop_id", "pet_id"])

    op.create_table(
        "visit_menus",
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("menu_id", sa.BigInteger, sa.ForeignKey("service_menus.id"), primary_key=True),
    )

    op.add_column(
        "customer_search_entries", sa.Column("last_visit_at", sa.DateTime(timezone=True))
    )
    op.create_index(
        "ix_customer_search_entries_shop_last_visit", "customer_search_entries",
        ["shop_id", "last_visit_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_customer_search_entries_shop_last_visit", table_name="customer_search_entries")
    op.drop_column("customer_search_entries", "last_visit_at")
    op.drop_table("visit_menus")
    op.drop_index("ix_visits_shop_pet", table_name="visits")
    op.drop_index("ix_visits_shop_customer", table_name="visits")
    op.drop_index("ix_visits_shop_starts_at", table_name="visits")
    op.drop_index("uq_visits_customer_start_active", table_name="visits")
    op.drop_index("uq_visits_pet_start_active", table_name="visits")
    op.drop_table("visits")
    op.drop_index("uq_service_menus_shop_name_active", table_name="service_menus")
    op.drop_index("ix_service_menus_shop_id", table_name="service_menus")
    op.drop_table("service_menus")
    op.drop_table("visit_closed_dates")
    op.drop_table("visit_weekly_closures")
    op.drop_table("visit_shop_settings")
