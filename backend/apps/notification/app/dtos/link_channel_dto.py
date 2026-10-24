from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class LinkChannelCommand:
    """토큰 신청 때와 같은 세 값 + 관리자 카카오톡으로 온 6자리."""

    ctx: ShopContext
    search_id: str
    admin_phone: str
    category_code: str
    token: str
