from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.guardian_form_port import GuardianFormPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.build_send_bundle_use_case import BuildSendBundleUseCase
from visit.app.use_cases.build_send_bundle_interactor import BuildSendBundleInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_guardian_forms, get_shop_profile
from visit.dependencies.visit_wiring import (
    build_check_repository,
    build_menu_repository,
    build_visit_repository,
    build_visit_series_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_build_send_bundle_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    forms: GuardianFormPort = Depends(get_guardian_forms),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> BuildSendBundleUseCase:
    visits = build_visit_repository(db)
    return BuildSendBundleInteractor(
        visits=visits, history=visits, menus=build_menu_repository(db), checks=build_check_repository(db),
        directory=directory, forms=forms, shops=shops, now=utc_now,
        series=build_visit_series_repository(db),
    )
