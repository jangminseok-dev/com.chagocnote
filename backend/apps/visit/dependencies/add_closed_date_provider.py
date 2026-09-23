from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.add_closed_date_use_case import AddClosedDateUseCase
from visit.app.use_cases.add_closed_date_interactor import AddClosedDateInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_add_closed_date_use_case(db: DbSession) -> AddClosedDateUseCase:
    return AddClosedDateInteractor(schedule=build_schedule_repository(db))
