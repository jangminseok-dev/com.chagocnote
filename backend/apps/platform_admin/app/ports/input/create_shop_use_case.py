from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.provisioned_shop import ProvisionedShop
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand


class CreateShopUseCase(ABC):
    @abstractmethod
    async def create_shop(self, command: CreateShopCommand) -> ProvisionedShop: ...
