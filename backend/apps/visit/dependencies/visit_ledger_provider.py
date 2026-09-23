from __future__ import annotations

from core.database import DbSession
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
from visit.dependencies.visit_wiring import build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_visit_ledger_use_case(db: DbSession) -> VisitLedgerPort:
    return VisitLedgerInteractor(visits=build_visit_repository(db), now=utc_now)
