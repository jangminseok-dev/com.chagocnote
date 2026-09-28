from __future__ import annotations

from core.database import DbSession
from hub.app.ports.shop_profile_port import ShopProfilePort
from tenancy.app.use_cases.get_shop_profile_interactor import GetShopProfileInteractor
from tenancy.dependencies.tenancy_wiring import build_shop_repository


def get_shop_profile_use_case(db: DbSession) -> ShopProfilePort:
    return GetShopProfileInteractor(shops=build_shop_repository(db))
