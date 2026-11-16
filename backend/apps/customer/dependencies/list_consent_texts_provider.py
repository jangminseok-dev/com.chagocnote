from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.list_consent_texts_use_case import ListConsentTextsUseCase
from customer.app.use_cases.list_consent_texts_interactor import ListConsentTextsInteractor
from customer.dependencies.customer_wiring import build_consent_text_repository


def get_list_consent_texts_use_case(db: DbSession) -> ListConsentTextsUseCase:
    return ListConsentTextsInteractor(texts=build_consent_text_repository(db))
