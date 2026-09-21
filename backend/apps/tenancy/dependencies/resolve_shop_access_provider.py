from __future__ import annotations

from core.database import DbSession
from hub.app.ports.shop_access_port import ShopAccessPort
from tenancy.app.use_cases.resolve_shop_access_interactor import ResolveShopAccessInteractor
from tenancy.dependencies.tenancy_wiring import build_member_repository


def get_resolve_shop_access_use_case(db: DbSession) -> ShopAccessPort:
    return ResolveShopAccessInteractor(members=build_member_repository(db))
