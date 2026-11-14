from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.media_library_port import MediaLibraryPort
from visit.app.ports.input.put_visit_record_use_case import PutVisitRecordUseCase
from visit.app.use_cases.put_visit_record_interactor import PutVisitRecordInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_domain_events, get_media_library
from visit.dependencies.visit_wiring import build_menu_repository, build_record_repository, build_visit_repository


def get_put_visit_record_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    library: MediaLibraryPort = Depends(get_media_library),
    events: DomainEventPort = Depends(get_domain_events),
) -> PutVisitRecordUseCase:
    visits = build_visit_repository(db)
    return PutVisitRecordInteractor(
        visits=visits, history=visits, records=build_record_repository(db), menus=build_menu_repository(db),
        directory=directory, library=library, events=events,
    )
