from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.sign_consent_in_shop_use_case import SignConsentInShopUseCase
from customer.app.use_cases.sign_consent_in_shop_interactor import SignConsentInShopInteractor
from customer.dependencies.customer_wiring import (
    build_consent_form_repository, build_consent_signature_repository, build_pet_repository, build_consent_source, utc_now,
)
from customer.domain.services.pet_age import seoul_today


def get_sign_consent_in_shop_use_case(db: DbSession) -> SignConsentInShopUseCase:
    return SignConsentInShopInteractor(
        pets=build_pet_repository(db), signatures=build_consent_signature_repository(db),
        forms=build_consent_form_repository(db), today=seoul_today, now=utc_now, source=build_consent_source(db),
    )
