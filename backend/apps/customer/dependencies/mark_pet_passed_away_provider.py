from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
from customer.app.use_cases.mark_pet_passed_away_interactor import MarkPetPassedAwayInteractor
from customer.dependencies.customer_wiring import (
    build_intake_form_repository, build_consent_form_repository,
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
    utc_now,
)
from customer.dependencies.hub_ports import get_visit_ledger
from customer.domain.services.pet_age import seoul_today
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_mark_pet_passed_away_use_case(
    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger)
) -> MarkPetPassedAwayUseCase:
    return MarkPetPassedAwayInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), ledger=ledger, today=seoul_today,
        forms=build_consent_form_repository(db), now=utc_now, intakes=build_intake_form_repository(db),
    )
