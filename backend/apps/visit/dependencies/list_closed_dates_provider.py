from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.list_closed_dates_use_case import ListClosedDatesUseCase
from visit.app.use_cases.list_closed_dates_interactor import ListClosedDatesInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_list_closed_dates_use_case(db: DbSession) -> ListClosedDatesUseCase:
    return ListClosedDatesInteractor(schedule=build_schedule_repository(db))
