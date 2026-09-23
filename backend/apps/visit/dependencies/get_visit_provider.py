from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import build_menu_repository, build_visit_repository


def get_get_visit_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> GetVisitUseCase:
    return GetVisitInteractor(
        visits=build_visit_repository(db), menus=build_menu_repository(db), directory=directory
    )
