from __future__ import annotations

from tenancy.adapter.outbound.orm.tenancy_orm import ShopInviteOrm, ShopMemberOrm, ShopOrm
from tenancy.domain.entities.invite import Invite
from tenancy.domain.entities.member import Member
from tenancy.domain.entities.shop import Shop
from tenancy.domain.value_objects.role_code import RoleCode


def to_shop(orm: ShopOrm) -> Shop:
    return Shop(
        id=orm.id,
        name=orm.name,
        business_type=orm.business_type,
        phone=orm.phone,
        address=orm.address,
        timezone=orm.timezone,
        suspended_at=orm.suspended_at,
        closed_at=orm.closed_at,
    )


def to_member(orm: ShopMemberOrm, role_code: str) -> Member:
    return Member(
        id=orm.id,
        shop_id=orm.shop_id,
        user_id=orm.user_id,
        role=RoleCode(role_code),
        joined_at=orm.joined_at,
    )


def to_invite(orm: ShopInviteOrm, role_code: str) -> Invite:
    return Invite(
        id=orm.id,
        shop_id=orm.shop_id,
        role=RoleCode(role_code),
        expires_at=orm.expires_at,
        max_uses=orm.max_uses,
        used_count=orm.used_count,
        revoked_at=orm.revoked_at,
    )
