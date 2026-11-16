from __future__ import annotations

from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
from core.database import DbSession
from customer.app.ports.input.issue_intake_form_use_case import IssueIntakeFormUseCase
from customer.app.use_cases.issue_intake_form_interactor import IssueIntakeFormInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository, build_form_settings_repository, build_intake_form_repository, build_pet_repository,
    utc_now,
)


def get_issue_intake_form_use_case(db: DbSession) -> IssueIntakeFormUseCase:
    return IssueIntakeFormInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        forms=build_intake_form_repository(db), settings=build_form_settings_repository(db), now=utc_now,
        link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
    )
