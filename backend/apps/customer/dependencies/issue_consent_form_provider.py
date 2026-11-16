from __future__ import annotations

from core.database import DbSession
from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
from customer.app.ports.input.issue_consent_form_use_case import IssueConsentFormUseCase
from customer.app.use_cases.issue_consent_form_interactor import IssueConsentFormInteractor
from customer.dependencies.customer_wiring import (
    build_consent_form_repository, build_consent_signature_repository, build_pet_repository, build_consent_source, utc_now,
)
from customer.domain.services.pet_age import seoul_today


def get_issue_consent_form_use_case(db: DbSession) -> IssueConsentFormUseCase:
    return IssueConsentFormInteractor(
        pets=build_pet_repository(db), signatures=build_consent_signature_repository(db),
        forms=build_consent_form_repository(db), today=seoul_today, now=utc_now, source=build_consent_source(db),
        link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
    )
