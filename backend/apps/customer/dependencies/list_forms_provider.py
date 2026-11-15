from __future__ import annotations

from core.database import DbSession
from core.config import REPORT_LINK_KEY, REPORT_WEB_BASE_URL
from customer.app.ports.input.list_forms_use_case import ListFormsUseCase
from customer.app.use_cases.list_forms_interactor import ListFormsInteractor
from customer.dependencies.customer_wiring import (
    build_consent_form_repository, build_customer_repository, build_pet_repository, utc_now,
)


def get_list_forms_use_case(db: DbSession) -> ListFormsUseCase:
    return ListFormsInteractor(
        forms=build_consent_form_repository(db), customers=build_customer_repository(db),
        pets=build_pet_repository(db), now=utc_now, link_key=REPORT_LINK_KEY, web_base_url=REPORT_WEB_BASE_URL,
    )
