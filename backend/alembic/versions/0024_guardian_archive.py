"""⑫ 보호자 기록 모아 보기 · 가족 · 리뷰 주소.

visit_shop_settings.report_review_url·report_review_text: 알림장 끝의 리뷰 남기기 줄(주소가 없으면 줄이 없다, 문구가 없으면 기본 문구).
visit_reports.show_review: 그 알림장에 리뷰 줄을 넣는가(알림장마다 뺄 수 있다 — 기본 넣음).

Revision ID: 0024
Revises: 0023
"""
from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visit_shop_settings", sa.Column("report_review_url", sa.String(300)))
    op.add_column("visit_shop_settings", sa.Column("report_review_text", sa.String(60)))
    op.add_column("visit_reports", sa.Column("show_review", sa.Boolean, nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("visit_reports", "show_review")
    op.drop_column("visit_shop_settings", "report_review_text")
    op.drop_column("visit_shop_settings", "report_review_url")
