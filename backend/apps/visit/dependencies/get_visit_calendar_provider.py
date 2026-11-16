from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
from visit.app.use_cases.get_visit_calendar_interactor import GetVisitCalendarInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import (
    build_record_repository,
    build_report_repository,
    build_revisit_settings_repository,
    build_schedule_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_get_visit_calendar_use_case(
    db: DbSession, library: MediaLibraryPort = Depends(get_media_library),
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
) -> GetVisitCalendarUseCase:
    return GetVisitCalendarInteractor(
        board=build_visit_repository(db), schedule=build_schedule_repository(db),
        records=build_record_repository(db), library=library, now=utc_now, reports=build_report_repository(db),
        revisit_settings=build_revisit_settings_repository(db), directory=directory,
    )
