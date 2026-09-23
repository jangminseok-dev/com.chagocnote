from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.adapter.outbound.rule_draft_parser_adapter import RuleDraftParserAdapter
from visit.app.ports.input.parse_visit_draft_use_case import ParseVisitDraftUseCase
from visit.app.use_cases.parse_visit_draft_interactor import ParseVisitDraftInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import build_menu_repository, build_schedule_repository
from visit.domain.services.visit_schedule import utc_now


def get_parse_visit_draft_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> ParseVisitDraftUseCase:
    return ParseVisitDraftInteractor(
        schedule=build_schedule_repository(db), menus=build_menu_repository(db), directory=directory,
        parser=RuleDraftParserAdapter(), now=utc_now,
    )
