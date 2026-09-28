from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_profile import ShopProfile


class ShopProfilePort(ABC):
    """구현: tenancy. 사용: visit(공개 알림장). 로그인한 사용자가 없는 자리에서 매장의 공개 정보를 읽는다."""

    @abstractmethod
    async def public_profile(self, shop_id: int) -> ShopProfile | None:
        """없는 매장이면 None. 정지했거나 폐업한 매장도 돌려준다 — 열지 말지는 open 을 보고 쓰는 쪽이 정한다.
        잠그지 않는다."""
