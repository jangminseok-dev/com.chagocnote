from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.app.dtos.update_shop_dto import UpdateShopCommand


class UpdateShopUseCase(ABC):
    @abstractmethod
    async def update_shop(self, command: UpdateShopCommand) -> ShopView: ...
