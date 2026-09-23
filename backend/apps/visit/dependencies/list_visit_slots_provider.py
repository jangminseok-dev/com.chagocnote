from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.list_visit_slots_use_case import ListVisitSlotsUseCase
from visit.app.use_cases.list_visit_slots_interactor import ListVisitSlotsInteractor
from visit.dependencies.visit_wiring import build_schedule_repository, build_visit_repository


def get_list_visit_slots_use_case(db: DbSession) -> ListVisitSlotsUseCase:
    return ListVisitSlotsInteractor(visits=build_visit_repository(db), schedule=build_schedule_repository(db))
