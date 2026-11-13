from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.get_visit_checks_use_case import GetVisitChecksUseCase
from visit.app.use_cases.get_visit_checks_interactor import GetVisitChecksInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import build_check_repository
from visit.domain.services.visit_schedule import utc_now


def get_get_visit_checks_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> GetVisitChecksUseCase:
    return GetVisitChecksInteractor(directory=directory, checks=build_check_repository(db), now=utc_now)
