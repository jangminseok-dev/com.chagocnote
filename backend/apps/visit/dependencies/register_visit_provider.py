from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_schedule_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_register_visit_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> RegisterVisitUseCase:
    visits = build_visit_repository(db)
    return RegisterVisitInteractor(
        visits=visits, board=visits, menus=build_menu_repository(db),
        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
    )
