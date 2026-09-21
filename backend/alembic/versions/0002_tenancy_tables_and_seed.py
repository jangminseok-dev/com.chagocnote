"""매장, 역할·권한, 소속, 초대 + 역할·권한 시드

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "shops",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("business_type", sa.String(30), server_default="pet_grooming", nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("address", sa.String(255)),
        sa.Column("timezone", sa.String(50), server_default="Asia/Seoul", nullable=False),
        sa.Column("suspended_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    roles = op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    permissions = op.create_table(
        "permissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("permission_id", sa.Integer, sa.ForeignKey("permissions.id"), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_pair"),
    )
    op.create_table(
        "shop_members",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),  # auth 의 유저 ID — 스포크를 넘는 외래 키는 걸지 않는다
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_shop_members_shop_id", "shop_members", ["shop_id"])
    op.create_index("ix_shop_members_user_id", "shop_members", ["user_id"])
    op.create_index(
        "uq_shop_members_active", "shop_members", ["shop_id", "user_id"],
        unique=True, postgresql_where=sa.text("removed_at IS NULL"),
    )
    op.create_table(
        "shop_invites",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("created_by_member_id", sa.Integer, sa.ForeignKey("shop_members.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer, server_default="1", nullable=False),
        sa.Column("used_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("code_hash", name="uq_shop_invites_code_hash"),
    )
    op.create_index("ix_shop_invites_shop_id", "shop_invites", ["shop_id"])

    op.bulk_insert(roles, [{"code": "owner", "name": "사장"}, {"code": "staff", "name": "직원"}])
    op.bulk_insert(
        permissions,
        [
            {"code": "reservation:write", "description": "예약 등록·수정"},
            {"code": "customer:write", "description": "고객·반려동물 등록·수정"},
            {"code": "record:write", "description": "미용 기록·사진 업로드"},
            {"code": "sales:write", "description": "기록할 때 매출 금액 입력"},
            {"code": "sales:read", "description": "매출 통계·합계 열람"},
            {"code": "record:delete", "description": "기록 삭제"},
            {"code": "customer:delete", "description": "고객 삭제"},
            {"code": "member:manage", "description": "직원 초대·내보내기·역할 변경"},
            {"code": "shop:update", "description": "매장 정보 수정"},
        ],
    )
    # 사장은 전부, 직원은 입력 권한 네 가지.
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'owner'
           OR (r.code = 'staff' AND p.code IN
               ('reservation:write', 'customer:write', 'record:write', 'sales:write'))
        """
    )


def downgrade() -> None:
    op.drop_index("ix_shop_invites_shop_id", table_name="shop_invites")
    op.drop_table("shop_invites")
    op.drop_index("uq_shop_members_active", table_name="shop_members")
    op.drop_index("ix_shop_members_user_id", table_name="shop_members")
    op.drop_index("ix_shop_members_shop_id", table_name="shop_members")
    op.drop_table("shop_members")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("shops")
