"""보호자용 읽기의 범위 — 가드가 확인한 연결(GuardianContext)의 매장을 읽어 읽기 전용 컨텍스트를 만든다."""
from __future__ import annotations

from hub.app.dtos.guardian import GuardianContext
from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.shop_profile_port import ShopProfilePort
from hub.app.dtos.shop_context import public_context


async def guardian_scope(
    guardian: GuardianContext, shops: ShopProfilePort
) -> tuple[ShopContext, ShopProfile] | None:
    """매장이 없거나 정지·폐업이면 None — 그 연결로는 아무것도 보이지 않는다(공개 알림장의 '닫힘'과 같다).

    보호자는 매장의 멤버가 아니다. 공개 조회와 같은 컨텍스트(권한 빔, 읽기 전용)를 쓴다 — 매장은 가드가
    계정으로 확인한 연결에서 읽은 것이다.
    """
    shop = await shops.public_profile(guardian.shop_id)
    if shop is None or not shop.open:
        return None
    return public_context(shop), shop
