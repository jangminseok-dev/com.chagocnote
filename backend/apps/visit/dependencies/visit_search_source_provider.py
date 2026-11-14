from __future__ import annotations

from core.database import DbSession
from hub.app.ports.search_source_port import SearchSourcePort
from visit.app.use_cases.visit_search_source_interactor import VisitSearchSourceInteractor
from visit.dependencies.visit_wiring import build_record_repository, build_visit_repository


def get_visit_search_source_use_case(db: DbSession) -> SearchSourcePort:
    """허브 포트 SearchSourcePort(scope "visit")의 구현 — main.py 가 색인기의 공장 자리에 꽂는다."""
    return VisitSearchSourceInteractor(visits=build_visit_repository(db), records=build_record_repository(db))
