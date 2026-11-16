from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.get_day_wrap_up_use_case import GetDayWrapUpUseCase
from visit.app.use_cases.get_day_wrap_up_interactor import GetDayWrapUpInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_record_repository,
    build_report_repository,
    build_revisit_settings_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_get_day_wrap_up_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> GetDayWrapUpUseCase:
    return GetDayWrapUpInteractor(
        board=build_visit_repository(db), menus=build_menu_repository(db), directory=directory,
        records=build_record_repository(db), library=library, reports=build_report_repository(db),
        revisit_settings=build_revisit_settings_repository(db), now=utc_now,
    )
