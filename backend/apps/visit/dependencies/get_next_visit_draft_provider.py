from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.app.use_cases.get_next_visit_draft_interactor import GetNextVisitDraftInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_revisit_settings_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_get_next_visit_draft_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory),
) -> GetNextVisitDraftUseCase:
    visits = build_visit_repository(db)
    return GetNextVisitDraftInteractor(
        visits=visits, history=visits, menus=build_menu_repository(db), directory=directory,
        settings=build_revisit_settings_repository(db), now=utc_now,
    )
