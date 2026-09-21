from __future__ import annotations

from fastapi import Depends

from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from platform_admin.app.ports.input.create_shop_use_case import CreateShopUseCase
from platform_admin.app.use_cases.create_shop_interactor import CreateShopInteractor
from platform_admin.dependencies.hub_ports import get_shop_provisioning


def get_create_shop_use_case(
    provisioning: ShopProvisioningPort = Depends(get_shop_provisioning),
) -> CreateShopUseCase:
    return CreateShopInteractor(provisioning=provisioning)
