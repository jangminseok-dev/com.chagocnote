from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class RequestChannelTokenCommand:
    """카카오톡 채널 연동 토큰 신청. 세 값은 업체에만 넘기고 저장하지 않는다(설계 6.2)."""

    ctx: ShopContext
    search_id: str
    admin_phone: str
    category_code: str
