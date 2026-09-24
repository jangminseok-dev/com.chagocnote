from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
from visit.app.use_cases.get_visit_calendar_interactor import GetVisitCalendarInteractor
from visit.dependencies.visit_wiring import build_schedule_repository, build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_get_visit_calendar_use_case(db: DbSession) -> GetVisitCalendarUseCase:
    return GetVisitCalendarInteractor(
        board=build_visit_repository(db), schedule=build_schedule_repository(db), now=utc_now
    )
