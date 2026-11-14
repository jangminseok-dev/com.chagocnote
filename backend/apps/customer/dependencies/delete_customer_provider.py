from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
)
from customer.dependencies.hub_ports import get_guardian_lifecycle, get_search_index, get_visit_ledger
from hub.app.ports.guardian_lifecycle_port import GuardianLifecyclePort
from hub.app.ports.search_index_port import SearchIndexPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_delete_customer_use_case(
    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger),
    guardians: GuardianLifecyclePort = Depends(get_guardian_lifecycle),
    index: SearchIndexPort = Depends(get_search_index),
) -> DeleteCustomerUseCase:
    return DeleteCustomerInteractor(
        customers=build_customer_repository(db), search=build_customer_search(db), ledger=ledger,
        guardians=guardians, index=index,
    )
