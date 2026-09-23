from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.delete_closed_date_use_case import DeleteClosedDateUseCase
from visit.app.use_cases.delete_closed_date_interactor import DeleteClosedDateInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_delete_closed_date_use_case(db: DbSession) -> DeleteClosedDateUseCase:
    return DeleteClosedDateInteractor(schedule=build_schedule_repository(db))
