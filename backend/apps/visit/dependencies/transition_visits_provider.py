from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.domain_event_port import DomainEventPort
from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
from visit.dependencies.hub_ports import get_customer_directory, get_domain_events
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_report_repository,
    build_revisit_settings_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_transition_visits_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory),
    events: DomainEventPort = Depends(get_domain_events),
) -> TransitionVisitsUseCase:
    visits = build_visit_repository(db)
    return TransitionVisitsInteractor(
        visits=visits, history=visits, menus=build_menu_repository(db), reports=build_report_repository(db),
        directory=directory, events=events, now=utc_now, settings=build_revisit_settings_repository(db),
    )
