from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from visit.app.ports.input.revoke_visit_report_use_case import RevokeVisitReportUseCase
from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
from visit.dependencies.visit_wiring import build_report_repository, build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_revoke_visit_report_use_case(
    db: DbSession,
    directory: CustomerDirectoryPort = Depends(get_customer_directory),
    events: DomainEventPort = Depends(get_domain_events),
) -> RevokeVisitReportUseCase:
    return RevokeVisitReportInteractor(
        visits=build_visit_repository(db), reports=build_report_repository(db), directory=directory, events=events,
        now=utc_now,
    )
