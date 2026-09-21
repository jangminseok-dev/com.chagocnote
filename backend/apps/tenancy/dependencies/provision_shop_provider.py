from __future__ import annotations

from core.database import DbSession
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from tenancy.app.use_cases.provision_shop_interactor import ProvisionShopInteractor
from tenancy.dependencies.tenancy_wiring import build_invite_repository, build_shop_repository


def get_provision_shop_use_case(db: DbSession) -> ShopProvisioningPort:
    return ProvisionShopInteractor(
        shops=build_shop_repository(db), invites=build_invite_repository(db)
    )
