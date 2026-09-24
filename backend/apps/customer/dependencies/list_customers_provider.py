from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from customer.app.ports.input.list_customers_use_case import ListCustomersUseCase
from customer.app.use_cases.list_customers_interactor import ListCustomersInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.dependencies.hub_ports import get_media_library, get_visit_ledger
from customer.domain.services.pet_age import seoul_today
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_list_customers_use_case(
    db: DbSession,
    ledger: VisitLedgerPort = Depends(get_visit_ledger),
    library: MediaLibraryPort = Depends(get_media_library),
) -> ListCustomersUseCase:
    return ListCustomersInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), ledger=ledger, library=library, today=seoul_today,
    )
