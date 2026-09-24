from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.delete_visit_record_use_case import DeleteVisitRecordUseCase
from visit.app.use_cases.delete_visit_record_interactor import DeleteVisitRecordInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_media_library
from visit.dependencies.visit_wiring import build_record_repository, build_visit_repository


def get_delete_visit_record_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
) -> DeleteVisitRecordUseCase:
    return DeleteVisitRecordInteractor(
        visits=build_visit_repository(db), records=build_record_repository(db), directory=directory,
        library=library,
    )
