from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.list_guardian_pets_use_case import ListGuardianPetsUseCase
from visit.app.use_cases.list_guardian_pets_interactor import ListGuardianPetsInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_shop_profile
from visit.dependencies.visit_wiring import build_report_repository


def get_list_guardian_pets_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> ListGuardianPetsUseCase:
    return ListGuardianPetsInteractor(build_report_repository(db), directory, shops)
