from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.list_visit_feed_use_case import ListVisitFeedUseCase
from visit.app.use_cases.list_visit_feed_interactor import ListVisitFeedInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository


def get_list_visit_feed_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> ListVisitFeedUseCase:
    return ListVisitFeedInteractor(
        feed=build_visit_repository(db), records=build_record_repository(db), menus=build_menu_repository(db),
        directory=directory, library=library,
    )
