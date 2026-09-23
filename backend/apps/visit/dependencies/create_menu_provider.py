from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.create_menu_use_case import CreateMenuUseCase
from visit.app.use_cases.create_menu_interactor import CreateMenuInteractor
from visit.dependencies.visit_wiring import build_menu_repository, build_schedule_repository


def get_create_menu_use_case(db: DbSession) -> CreateMenuUseCase:
    return CreateMenuInteractor(schedule=build_schedule_repository(db), menus=build_menu_repository(db))
