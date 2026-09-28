from __future__ import annotations

from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.shop_profile_port import ShopProfilePort
from tenancy.app.ports.output.shop_repository import ShopRepository


class GetShopProfileInteractor(ShopProfilePort):
    """허브의 ShopProfilePort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, shops: ShopRepository) -> None:
        self._shops = shops

    async def public_profile(self, shop_id: int) -> ShopProfile | None:
        shop = await self._shops.find_by_id(shop_id)
        if shop is None:
            return None
        return ShopProfile(
            shop_id=shop.id,
            name=shop.name,
            phone=shop.phone,
            address=shop.address,
            timezone=shop.timezone,
            open=shop.suspended_at is None and shop.closed_at is None,
        )
