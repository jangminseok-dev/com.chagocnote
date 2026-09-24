from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.app.use_cases.get_next_visit_draft_interactor import GetNextVisitDraftInteractor
from visit.dependencies.visit_wiring import build_menu_repository, build_visit_repository


def get_get_next_visit_draft_use_case(db: DbSession) -> GetNextVisitDraftUseCase:
    visits = build_visit_repository(db)
    return GetNextVisitDraftInteractor(visits=visits, history=visits, menus=build_menu_repository(db))
