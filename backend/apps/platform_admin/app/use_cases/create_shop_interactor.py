from __future__ import annotations

from hub.app.dtos.provisioned_shop import ProvisionedShop
from hub.app.ports.operator_directory_port import OperatorDirectoryPort
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand
from platform_admin.app.ports.input.create_shop_use_case import CreateShopUseCase
from platform_admin.domain.errors import NotAnOperatorError


class CreateShopInteractor(CreateShopUseCase):
    def __init__(self, operators: OperatorDirectoryPort, provisioning: ShopProvisioningPort) -> None:
        self._operators = operators
        self._provisioning = provisioning

    async def create_shop(self, command: CreateShopCommand) -> ProvisionedShop:
        if not await self._operators.is_operator(command.user_id):
            raise NotAnOperatorError("플랫폼 운영자만 쓸 수 있습니다.")
        return await self._provisioning.create_shop(command.name, command.business_type)
