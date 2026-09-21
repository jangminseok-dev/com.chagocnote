from __future__ import annotations

from pydantic import BaseModel

from tenancy.app.dtos.shop_view_dto import ShopView


class ShopResponseSchema(BaseModel):
    shop_id: int
    name: str
    business_type: str
    phone: str | None
    address: str | None
    timezone: str

    @classmethod
    def of(cls, view: ShopView) -> ShopResponseSchema:
        return cls(
            shop_id=view.shop_id, name=view.name, business_type=view.business_type,
            phone=view.phone, address=view.address, timezone=view.timezone,
        )
