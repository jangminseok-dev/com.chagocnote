from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
from customer.dependencies.customer_wiring import (
    build_intake_form_repository, build_consent_form_repository,
    build_consent_signature_repository,
    build_customer_search,
    build_pet_repository,
    utc_now,
)
from customer.dependencies.hub_ports import get_domain_events, get_visit_ledger
from hub.app.ports.domain_event_port import DomainEventPort
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_delete_pet_use_case(
    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger),
    events: DomainEventPort = Depends(get_domain_events),
) -> DeletePetUseCase:
    return DeletePetInteractor(
        pets=build_pet_repository(db), search=build_customer_search(db), ledger=ledger,
        events=events, forms=build_consent_form_repository(db),
        signatures=build_consent_signature_repository(db), now=utc_now, intakes=build_intake_form_repository(db),
    )
