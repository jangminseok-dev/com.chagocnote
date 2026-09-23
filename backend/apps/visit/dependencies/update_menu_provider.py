from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.update_menu_use_case import UpdateMenuUseCase
from visit.app.use_cases.update_menu_interactor import UpdateMenuInteractor
from visit.dependencies.visit_wiring import build_menu_repository


def get_update_menu_use_case(db: DbSession) -> UpdateMenuUseCase:
    return UpdateMenuInteractor(menus=build_menu_repository(db))
