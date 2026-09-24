"""미디어 객체 표(media 스포크)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_objects",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),   # tenancy 의 매장 ID — 외래 키 없음
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("object_key", sa.String(100), nullable=False),
        sa.Column("display_key", sa.String(100)),
        sa.Column("thumb_key", sa.String(100), nullable=False),
        sa.Column("content_type", sa.String(20), nullable=False),
        sa.Column("size_bytes", sa.BigInteger),
        sa.Column("width", sa.SmallInteger, nullable=False),
        sa.Column("height", sa.SmallInteger, nullable=False),
        sa.Column("duration_seconds", sa.SmallInteger),
        sa.Column("uploaded_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN ('photo', 'video')", name="ck_media_objects_kind"),
        sa.CheckConstraint("status IN ('pending', 'ready')", name="ck_media_objects_status"),
        sa.CheckConstraint(
            "(status = 'ready') = (ready_at IS NOT NULL) AND (status = 'ready') = (size_bytes IS NOT NULL)",
            name="ck_media_objects_ready_fields",
        ),
        sa.CheckConstraint("attached_at IS NULL OR status = 'ready'", name="ck_media_objects_attached_ready"),
        sa.CheckConstraint("(kind = 'photo') = (display_key IS NOT NULL)", name="ck_media_objects_display"),
        sa.CheckConstraint("(kind = 'video') = (duration_seconds IS NOT NULL)", name="ck_media_objects_duration"),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_media_objects_size"),
        sa.UniqueConstraint("object_key", name="media_objects_object_key_key"),
        sa.UniqueConstraint("display_key", name="media_objects_display_key_key"),
        sa.UniqueConstraint("thumb_key", name="media_objects_thumb_key_key"),
    )
    op.create_index(
        "ix_media_objects_shop_status_created", "media_objects", ["shop_id", "status", "created_at"]
    )
    op.create_index(
        "ix_media_objects_unattached", "media_objects", ["ready_at"],
        postgresql_where=sa.text("status = 'ready' AND attached_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_media_objects_unattached", table_name="media_objects")
    op.drop_index("ix_media_objects_shop_status_created", table_name="media_objects")
    op.drop_table("media_objects")
