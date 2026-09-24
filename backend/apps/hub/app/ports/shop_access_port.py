from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext


class ShopAccessPort(ABC):
    """구현: tenancy. 사용: 매장 범위의 모든 스포크 (core/shop_guard.py 를 거쳐서)."""

    @abstractmethod
    async def resolve(self, user_id: int, shop_id: int) -> ShopContext:
        """소속·역할·권한과 매장 상태를 매 요청마다 DB 에서 확인한다.

        통과하지 못하면 허브 오류를 던진다: ShopAccessDeniedError(멤버가 아니거나 매장이 없음 — 둘을 구분해
        주지 않는다), ShopAccessClosedError, ShopAccessSuspendedError.
        """
