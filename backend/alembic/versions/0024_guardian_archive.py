"""⑫ 보호자 기록 모아 보기 · 가족 · 리뷰 주소.

visit_shop_settings.report_review_url·report_review_text: 알림장 끝의 리뷰 남기기 줄(주소가 없으면 줄이 없다, 문구가 없으면 기본 문구).
visit_reports.show_review: 그 알림장에 리뷰 줄을 넣는가(알림장마다 뺄 수 있다 — 기본 넣음).
guardian_links.parent_link_id·seen_by_primary_at: 가족 연결(기본 연결 아래의 줄). 기본 연결은 여전히 카드당 하나다.
guardian_family_invites: 가족 초대(코드는 SHA-256 만, 24시간·한 번). guardian_shop_settings: 매장이 정하는 가족 수(0~10, 기본 3).

Revision ID: 0024
Revises: 0023
"""
from alembic import op
import sqlalchemy as sa

_VERIFIED = "ck_guardian_links_verified_by"
_ENDED = "ck_guardian_links_ended_by"
_LIVE = "uq_guardian_links_live"

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visit_shop_settings", sa.Column("report_review_url", sa.String(300)))
    op.add_column("visit_shop_settings", sa.Column("report_review_text", sa.String(60)))
    op.add_column("visit_reports", sa.Column("show_review", sa.Boolean, nullable=False, server_default=sa.true()))

    op.add_column("guardian_links", sa.Column("parent_link_id", sa.BigInteger, sa.ForeignKey("guardian_links.id")))
    op.add_column("guardian_links", sa.Column("seen_by_primary_at", sa.DateTime(timezone=True)))
    op.drop_constraint(_VERIFIED, "guardian_links", type_="check")
    op.create_check_constraint(_VERIFIED, "guardian_links", "verified_by IN ('report_link', 'family_invite')")
    op.drop_constraint(_ENDED, "guardian_links", type_="check")
    op.create_check_constraint(
        _ENDED, "guardian_links",
        "ended_by IS NULL OR ended_by IN ('guardian', 'shop', 'withdrawn', 'anonymized', 'primary')")
    op.create_check_constraint(
        "ck_guardian_links_family", "guardian_links", "(parent_link_id IS NULL) = (verified_by <> 'family_invite')")
    op.drop_index(_LIVE, "guardian_links")
    op.create_index(_LIVE, "guardian_links", ["shop_id", "customer_id"], unique=True,
                    postgresql_where=sa.text("ended_at IS NULL AND parent_link_id IS NULL"))
    op.create_index("uq_guardian_links_family", "guardian_links", ["parent_link_id", "user_id"], unique=True,
                    postgresql_where=sa.text("ended_at IS NULL AND parent_link_id IS NOT NULL"))
    op.create_table(
        "guardian_family_invites",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("link_id", sa.BigInteger, sa.ForeignKey("guardian_links.id"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("code_hash", name="uq_guardian_family_invites_code_hash"),
    )
    op.create_index("ix_guardian_family_invites_link_id", "guardian_family_invites", ["link_id"])
    op.create_table(
        "guardian_shop_settings",
        sa.Column("shop_id", sa.BigInteger, primary_key=True),
        sa.Column("family_max", sa.SmallInteger, nullable=False, server_default="3"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("family_max BETWEEN 0 AND 10", name="ck_guardian_shop_settings_family_max"),
    )


def downgrade() -> None:
    op.drop_table("guardian_shop_settings")
    op.drop_index("ix_guardian_family_invites_link_id", "guardian_family_invites")
    op.drop_table("guardian_family_invites")
    op.execute("DELETE FROM guardian_links WHERE parent_link_id IS NOT NULL")
    op.drop_index("uq_guardian_links_family", "guardian_links")
    op.drop_index(_LIVE, "guardian_links")
    op.create_index(_LIVE, "guardian_links", ["shop_id", "customer_id"], unique=True,
                    postgresql_where=sa.text("ended_at IS NULL"))
    op.drop_constraint("ck_guardian_links_family", "guardian_links", type_="check")
    op.drop_constraint(_ENDED, "guardian_links", type_="check")
    op.execute("UPDATE guardian_links SET ended_by = 'guardian' WHERE ended_by = 'primary'")
    op.create_check_constraint(
        _ENDED, "guardian_links", "ended_by IS NULL OR ended_by IN ('guardian', 'shop', 'withdrawn', 'anonymized')")
    op.drop_constraint(_VERIFIED, "guardian_links", type_="check")
    op.create_check_constraint(_VERIFIED, "guardian_links", "verified_by IN ('report_link')")
    op.drop_column("guardian_links", "seen_by_primary_at")
    op.drop_column("guardian_links", "parent_link_id")
    op.drop_column("visit_reports", "show_review")
    op.drop_column("visit_shop_settings", "report_review_text")
    op.drop_column("visit_shop_settings", "report_review_url")
