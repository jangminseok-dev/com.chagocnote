from __future__ import annotations

from dataclasses import dataclass

from tenancy.domain.entities.shop import Shop


@dataclass(frozen=True)
class ShopView:
    """멤버에게 보여 주는 매장 정보. 정지·닫힘 시각은 넣지 않는다 (그런 매장은 소속 확인에서 이미 막힌다)."""

    shop_id: int
    name: str
    business_type: str
    phone: str | None
    address: str | None
    timezone: str

    @classmethod
    def of(cls, shop: Shop) -> ShopView:
        return cls(
            shop_id=shop.id, name=shop.name, business_type=shop.business_type,
            phone=shop.phone, address=shop.address, timezone=shop.timezone,
        )
