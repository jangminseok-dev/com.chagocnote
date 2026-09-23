from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.archive_menu_use_case import ArchiveMenuUseCase
from visit.app.use_cases.archive_menu_interactor import ArchiveMenuInteractor
from visit.dependencies.visit_wiring import build_menu_repository


def get_archive_menu_use_case(db: DbSession) -> ArchiveMenuUseCase:
    return ArchiveMenuInteractor(menus=build_menu_repository(db))
