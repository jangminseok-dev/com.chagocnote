from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.read_guardian_weights_use_case import ReadGuardianWeightsUseCase
from visit.app.use_cases.read_guardian_weights_interactor import ReadGuardianWeightsInteractor
from visit.dependencies.hub_ports import get_shop_profile
from visit.dependencies.visit_wiring import build_report_repository, build_report_settings_repository


def get_read_guardian_weights_use_case(
    db: DbSession, shops: ShopProfilePort = Depends(get_shop_profile),
) -> ReadGuardianWeightsUseCase:
    return ReadGuardianWeightsInteractor(build_report_repository(db), build_report_settings_repository(db), shops)
