from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListMembersQuery:
    ctx: ShopContext


@dataclass(frozen=True)
class MemberView:
    member_id: int
    user_id: int
    display_name: str
    profile_image_url: str | None
    role: str
    joined_at: datetime
