from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from search.app.ports.input.search_records_use_case import SearchRecordsUseCase
from search.app.use_cases.search_records_interactor import SearchRecordsInteractor
from search.dependencies.hub_ports import get_customer_directory, get_media_library, get_visit_ledger
from search.dependencies.search_wiring import build_candidate_repository, get_embedder


def get_search_records_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    ledger: VisitLedgerPort = Depends(get_visit_ledger),
    library: MediaLibraryPort = Depends(get_media_library),
) -> SearchRecordsUseCase:
    return SearchRecordsInteractor(
        candidates=build_candidate_repository(db), embedder=get_embedder(), directory=directory, ledger=ledger,
        library=library,
    )
