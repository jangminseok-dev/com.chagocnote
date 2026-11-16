from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.revoke_form_use_case import RevokeFormUseCase
from customer.app.use_cases.revoke_form_interactor import RevokeFormInteractor
from customer.dependencies.customer_wiring import build_intake_form_repository, build_consent_form_repository, build_customer_repository, utc_now


def get_revoke_form_use_case(db: DbSession) -> RevokeFormUseCase:
    return RevokeFormInteractor(
        forms=build_consent_form_repository(db), customers=build_customer_repository(db), now=utc_now,
        intakes=build_intake_form_repository(db))
