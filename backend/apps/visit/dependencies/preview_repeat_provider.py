from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.preview_repeat_use_case import PreviewRepeatUseCase
from visit.app.use_cases.preview_repeat_interactor import PreviewRepeatInteractor
from visit.dependencies.visit_wiring import build_menu_repository, build_schedule_repository, build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_preview_repeat_use_case(db: DbSession) -> PreviewRepeatUseCase:
    visits = build_visit_repository(db)
    return PreviewRepeatInteractor(
        visits, visits, build_menu_repository(db), build_schedule_repository(db), now=utc_now)
