from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_visit_defaults_use_case import GetVisitDefaultsUseCase
from visit.app.use_cases.get_visit_defaults_interactor import GetVisitDefaultsInteractor
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_schedule_repository,
    build_visit_repository,
)


def get_get_visit_defaults_use_case(db: DbSession) -> GetVisitDefaultsUseCase:
    return GetVisitDefaultsInteractor(
        history=build_visit_repository(db), menus=build_menu_repository(db), schedule=build_schedule_repository(db)
    )
