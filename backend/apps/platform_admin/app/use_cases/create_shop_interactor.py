from __future__ import annotations

from hub.app.dtos.provisioned_shop import ProvisionedShop
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand
from platform_admin.app.ports.input.create_shop_use_case import CreateShopUseCase


class CreateShopInteractor(CreateShopUseCase):
    """운영자 확인은 라우터의 require_operator 가드가 한다. 같은 확인을 두 번 하지 않는다."""

    def __init__(self, provisioning: ShopProvisioningPort) -> None:
        self._provisioning = provisioning

    async def create_shop(self, command: CreateShopCommand) -> ProvisionedShop:
        return await self._provisioning.create_shop(command.name, command.business_type)
