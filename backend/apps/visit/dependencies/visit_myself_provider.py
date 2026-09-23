from __future__ import annotations

from visit.adapter.outbound.log_visit_myself_record_adapter import LogVisitMyselfRecordAdapter
from visit.app.ports.input.visit_myself_use_case import VisitMyselfUseCase
from visit.app.use_cases.visit_myself_interactor import VisitMyselfInteractor


def get_visit_myself_use_case() -> VisitMyselfUseCase:
    return VisitMyselfInteractor(record=LogVisitMyselfRecordAdapter())
