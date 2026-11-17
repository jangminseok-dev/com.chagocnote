from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.get_visit_series_use_case import GetVisitSeriesUseCase
from visit.app.use_cases.get_visit_series_interactor import GetVisitSeriesInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_visit_repository,
    build_visit_series_repository,
)


def get_get_visit_series_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory),
) -> GetVisitSeriesUseCase:
    return GetVisitSeriesInteractor(
        build_visit_repository(db), build_visit_series_repository(db), directory, build_menu_repository(db))
