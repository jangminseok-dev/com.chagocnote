"""미용 알림장 — 링크(visit_reports), 뺀 사진 칸, 매장 설정 칸

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_SHOWN = {"report_show_menus": "true", "report_show_shop_info": "true",
          "report_show_weight": "false", "report_show_amount": "false"}


def upgrade() -> None:
    op.create_table(
        "visit_reports",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("public_id", sa.LargeBinary(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),          # NULL 이면 무기한
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("first_viewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),   # tenancy 의 멤버 ID — 외래 키 없음
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("expires_at IS NULL OR expires_at > created_at", name="ck_visit_reports_expires"),
        sa.CheckConstraint("octet_length(public_id) = 16", name="ck_visit_reports_public_id"),
        sa.UniqueConstraint("public_id", name="visit_reports_public_id_key"),
    )
    # 방문당 끊지 않은 줄은 하나. 색인에 현재 시각을 넣을 수 없어 기간이 지난 줄은 발급이 먼저 닫는다.
    op.create_index(
        "uq_visit_reports_live", "visit_reports", ["visit_id"], unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.add_column(
        "visit_record_media",
        sa.Column("hidden_from_report", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )
    # NULL 은 무기한이다 — 이미 있는 매장 행은 server_default 로 30 을 받는다.
    op.add_column("visit_shop_settings", sa.Column("report_link_days", sa.SmallInteger, server_default=sa.text("30")))
    op.create_check_constraint(
        "ck_visit_shop_settings_report_link_days", "visit_shop_settings",
        "report_link_days IS NULL OR report_link_days IN (7, 30)",
    )
    for name, default in _SHOWN.items():
        op.add_column(
            "visit_shop_settings", sa.Column(name, sa.Boolean, server_default=sa.text(default), nullable=False)
        )


def downgrade() -> None:
    for name in reversed(_SHOWN):
        op.drop_column("visit_shop_settings", name)
    op.drop_constraint("ck_visit_shop_settings_report_link_days", "visit_shop_settings", type_="check")
    op.drop_column("visit_shop_settings", "report_link_days")
    op.drop_column("visit_record_media", "hidden_from_report")
    op.drop_index("uq_visit_reports_live", table_name="visit_reports")
    op.drop_table("visit_reports")
