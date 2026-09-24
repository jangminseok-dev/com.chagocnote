from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
from visit.app.use_cases.list_day_visits_interactor import ListDayVisitsInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_record_repository,
    build_schedule_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_list_day_visits_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> ListDayVisitsUseCase:
    return ListDayVisitsInteractor(
        board=build_visit_repository(db), menus=build_menu_repository(db),
        schedule=build_schedule_repository(db), directory=directory, records=build_record_repository(db),
        library=library, now=utc_now,
    )
