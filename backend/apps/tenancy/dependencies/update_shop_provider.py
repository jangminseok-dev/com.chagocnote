from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.update_shop_use_case import UpdateShopUseCase
from tenancy.app.use_cases.update_shop_interactor import UpdateShopInteractor
from tenancy.dependencies.tenancy_wiring import build_shop_repository


def get_update_shop_use_case(db: DbSession) -> UpdateShopUseCase:
    return UpdateShopInteractor(shops=build_shop_repository(db))
