from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.read_guardian_report_use_case import ReadGuardianReportUseCase
from visit.app.use_cases.read_guardian_report_interactor import ReadGuardianReportInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library, get_shop_profile
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_record_repository,
    build_report_repository,
    build_report_settings_repository,
)


def get_read_guardian_report_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> ReadGuardianReportUseCase:
    return ReadGuardianReportInteractor(
        build_report_repository(db), build_record_repository(db), build_report_settings_repository(db),
        build_menu_repository(db), directory, library, shops,
    )
