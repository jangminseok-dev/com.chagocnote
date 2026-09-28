from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from visit.app.ports.input.send_visit_report_use_case import SendVisitReportUseCase
from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library, get_shop_profile
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_record_repository,
    build_report_repository,
    build_report_settings_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_send_visit_report_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
    shops: ShopProfilePort = Depends(get_shop_profile),
) -> SendVisitReportUseCase:
    return SendVisitReportInteractor(
        visits=build_visit_repository(db), records=build_record_repository(db),
        settings=build_report_settings_repository(db), reports=build_report_repository(db),
        menus=build_menu_repository(db), directory=directory, library=library, shops=shops, now=utc_now,
        link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
    )
