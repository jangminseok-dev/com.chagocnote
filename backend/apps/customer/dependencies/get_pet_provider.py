from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from customer.app.ports.input.get_pet_use_case import GetPetUseCase
from customer.app.use_cases.get_pet_interactor import GetPetInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_pet_repository,
)
from customer.dependencies.hub_ports import get_media_library, get_visit_ledger
from customer.domain.services.pet_age import seoul_today
from hub.app.ports.media_library_port import MediaLibraryPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_get_pet_use_case(
    db: DbSession,
    ledger: VisitLedgerPort = Depends(get_visit_ledger),
    library: MediaLibraryPort = Depends(get_media_library),
) -> GetPetUseCase:
    return GetPetInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), ledger=ledger, library=library,
        today=seoul_today,
    )
