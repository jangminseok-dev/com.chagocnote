from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_pet_repository,
)
from customer.dependencies.hub_ports import get_visit_ledger
from customer.domain.services.pet_age import seoul_today
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_get_customer_use_case(
    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger)
) -> GetCustomerUseCase:
    return GetCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), ledger=ledger,
        today=seoul_today,
    )
