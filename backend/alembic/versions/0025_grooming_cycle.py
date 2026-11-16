"""⑬ 아이별 미용 주기 · 다시 올 때가 된 아이 · 결제 완료와 남은 일 · 하루 마무리.

pets.grooming_cycle_weeks: 그 아이에게 직접 정한 미용 주기(1~52주, 없으면 지난 방문에서 계산한다).
pets.revisit_nudged_on: 다시 올 때가 됐다고 안내한 날(공유 시트를 연 날 — 보냈는지는 모른다).
visit_shop_settings: 매장의 기본 간격(4주), '곧'으로 치는 날 수(7일), 안내 글 템플릿(없으면 처음 글),
  알림장을 남은 일로 세기(켬), 주기를 계산할 때 볼 최근 방문 수(6번), 손질로 보고 뺄 날 수(7일).
visits.report_skipped_at: 하루 마무리에서 "알림장을 보내지 않음"으로 넘긴 때.

Revision ID: 0025
Revises: 0024
"""
from alembic import op
import sqlalchemy as sa

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

_SETTINGS = (
    ("default_cycle_weeks", "4", "default_cycle_weeks BETWEEN 1 AND 52"),
    ("revisit_soon_days", "7", "revisit_soon_days BETWEEN 1 AND 30"),
    ("cycle_sample_visits", "6", "cycle_sample_visits BETWEEN 3 AND 12"),
    ("cycle_min_gap_days", "7", "cycle_min_gap_days BETWEEN 0 AND 28"),
)


def upgrade() -> None:
    op.add_column("pets", sa.Column("grooming_cycle_weeks", sa.SmallInteger))
    op.add_column("pets", sa.Column("revisit_nudged_on", sa.Date))
    op.create_check_constraint(
        "ck_pets_grooming_cycle_weeks", "pets",
        "grooming_cycle_weeks IS NULL OR grooming_cycle_weeks BETWEEN 1 AND 52")
    for name, default, check in _SETTINGS:
        op.add_column("visit_shop_settings",
                      sa.Column(name, sa.SmallInteger, nullable=False, server_default=default))
        op.create_check_constraint(f"ck_visit_shop_settings_{name}", "visit_shop_settings", check)
    op.add_column("visit_shop_settings", sa.Column("revisit_message", sa.String(300)))
    op.add_column("visit_shop_settings",
                  sa.Column("count_unsent_reports", sa.Boolean, nullable=False, server_default=sa.true()))
    op.add_column("visits", sa.Column("report_skipped_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("visits", "report_skipped_at")
    op.drop_column("visit_shop_settings", "count_unsent_reports")
    op.drop_column("visit_shop_settings", "revisit_message")
    for name, _, _ in reversed(_SETTINGS):
        op.drop_constraint(f"ck_visit_shop_settings_{name}", "visit_shop_settings", type_="check")
        op.drop_column("visit_shop_settings", name)
    op.drop_constraint("ck_pets_grooming_cycle_weeks", "pets", type_="check")
    op.drop_column("pets", "revisit_nudged_on")
    op.drop_column("pets", "grooming_cycle_weeks")
