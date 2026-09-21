from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ChangeMemberRoleCommand:
    ctx: ShopContext
    member_id: int
    role: str  # "owner" 또는 "staff" — 스키마가 걸러 준다


@dataclass(frozen=True)
class ChangedMember:
    member_id: int
    user_id: int
    role: str
