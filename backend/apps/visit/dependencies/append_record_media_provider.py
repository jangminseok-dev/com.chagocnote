from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.append_record_media_use_case import AppendRecordMediaUseCase
from visit.app.use_cases.append_record_media_interactor import AppendRecordMediaInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository


def get_append_record_media_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> AppendRecordMediaUseCase:
    return AppendRecordMediaInteractor(
        visits=build_visit_repository(db), records=build_record_repository(db), menus=build_menu_repository(db),
        directory=directory, library=library,
    )
