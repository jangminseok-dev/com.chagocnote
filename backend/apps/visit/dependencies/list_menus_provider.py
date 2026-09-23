from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.list_menus_use_case import ListMenusUseCase
from visit.app.use_cases.list_menus_interactor import ListMenusInteractor
from visit.dependencies.visit_wiring import build_menu_repository, build_schedule_repository


def get_list_menus_use_case(db: DbSession) -> ListMenusUseCase:
    return ListMenusInteractor(schedule=build_schedule_repository(db), menus=build_menu_repository(db))
