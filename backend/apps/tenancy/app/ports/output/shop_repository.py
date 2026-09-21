from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from tenancy.domain.entities.shop import Shop


class ShopRepository(ABC):
    @abstractmethod
    async def create(self, name: str, business_type: str) -> Shop: ...

    @abstractmethod
    async def get_by_id(self, shop_id: int) -> Shop:
        """컨텍스트가 아직 없는 경로(초대 수락)에서만 쓴다."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> Shop: ...

    @abstractmethod
    async def update(
        self, ctx: ShopContext, name: str, phone: str | None, address: str | None
    ) -> Shop: ...
