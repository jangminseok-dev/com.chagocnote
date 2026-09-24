from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository


def get_get_visit_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> GetVisitUseCase:
    visits = build_visit_repository(db)
    return GetVisitInteractor(
        visits=visits, history=visits, ledger=visits, menus=build_menu_repository(db), directory=directory,
        records=build_record_repository(db), library=library,
    )
