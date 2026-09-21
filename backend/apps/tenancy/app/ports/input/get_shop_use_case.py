from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.get_shop_dto import GetShopQuery
from tenancy.app.dtos.shop_view_dto import ShopView


class GetShopUseCase(ABC):
    @abstractmethod
    async def get_shop(self, query: GetShopQuery) -> ShopView: ...
