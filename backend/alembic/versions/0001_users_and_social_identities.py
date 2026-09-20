"""유저와 소셜 신원

Revision ID: 0001
Revises:
Create Date: 2026-09-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("profile_image_url", sa.String(500)),
        sa.Column("phone", sa.String(20)),
        sa.Column("suspended_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "social_identities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("provider_refresh_token_enc", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_social_identities_provider_user"),
    )
    op.create_index("ix_social_identities_user_id", "social_identities", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_social_identities_user_id", table_name="social_identities")
    op.drop_table("social_identities")
    op.drop_table("users")
