from __future__ import annotations

from core.database import DbSession
from customer.app.use_cases.guardian_form_interactor import GuardianFormInteractor
from customer.dependencies.customer_wiring import build_form_settings_repository
from customer.dependencies.issue_consent_form_provider import get_issue_consent_form_use_case
from hub.app.ports.guardian_form_port import GuardianFormPort


def get_guardian_form_use_case(db: DbSession) -> GuardianFormPort:
    return GuardianFormInteractor(
        issue=get_issue_consent_form_use_case(db), settings=build_form_settings_repository(db))
