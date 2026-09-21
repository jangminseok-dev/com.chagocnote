from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.get_shop_use_case import GetShopUseCase
from tenancy.app.use_cases.get_shop_interactor import GetShopInteractor
from tenancy.dependencies.tenancy_wiring import build_shop_repository


def get_get_shop_use_case(db: DbSession) -> GetShopUseCase:
    return GetShopInteractor(shops=build_shop_repository(db))
