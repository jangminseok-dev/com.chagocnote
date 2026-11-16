from __future__ import annotations

from core.database import DbSession
from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_consent_form_repository,
    build_consent_signature_repository,
    build_customer_search,
    build_family_brief_repository,
    build_pet_repository,
    utc_now,
)
from hub.app.ports.customer_directory_port import CustomerDirectoryPort


def get_customer_directory_use_case(db: DbSession) -> CustomerDirectoryPort:
    return CustomerDirectoryInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        briefs=build_family_brief_repository(db), search=build_customer_search(db),
        signatures=build_consent_signature_repository(db), forms=build_consent_form_repository(db), now=utc_now,
    )
