from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
from visit.app.use_cases.update_visit_interactor import UpdateVisitInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_schedule_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_update_visit_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> UpdateVisitUseCase:
    visits = build_visit_repository(db)
    return UpdateVisitInteractor(
        visits=visits, board=visits, menus=build_menu_repository(db),
        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
    )
