from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.set_report_skip_use_case import SetReportSkipUseCase
from visit.app.use_cases.set_report_skip_interactor import SetReportSkipInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import build_record_repository, build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_set_report_skip_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory),
) -> SetReportSkipUseCase:
    return SetReportSkipInteractor(
        visits=build_visit_repository(db), records=build_record_repository(db), directory=directory, now=utc_now,
    )
