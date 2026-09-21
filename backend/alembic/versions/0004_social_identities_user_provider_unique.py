"""소셜 신원: 한 유저는 제공자마다 하나만

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-21
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_social_identities_user_provider", "social_identities", ["user_id", "provider"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_social_identities_user_provider", "social_identities", type_="unique")
