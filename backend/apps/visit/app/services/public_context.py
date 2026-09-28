from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile


def public_context(shop: ShopProfile) -> ShopContext:
    """로그인이 없는 공개 조회가 쓰는 매장 컨텍스트. 권한이 비어 있고 읽기에만 쓴다.

    멤버가 없어 member_id 는 0 이다. 매장은 서명을 확인한 토큰의 링크에서 읽은 것이어야 한다.
    """
    return ShopContext(
        shop_id=shop.shop_id, member_id=0, role="public", permissions=frozenset(), timezone=shop.timezone)
