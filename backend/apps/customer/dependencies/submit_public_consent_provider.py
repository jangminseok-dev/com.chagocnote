from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY
from core.database import DbSession
from customer.app.ports.input.submit_public_consent_use_case import SubmitPublicConsentUseCase
from customer.app.use_cases.submit_public_consent_interactor import SubmitPublicConsentInteractor
from customer.dependencies.customer_wiring import (
    build_consent_form_repository, build_consent_signature_repository, build_customer_repository,
    build_pet_repository, build_public_form_limiter, build_consent_source, utc_now,
)
from customer.dependencies.hub_ports import get_shop_profile
from hub.app.ports.shop_profile_port import ShopProfilePort


def get_submit_public_consent_use_case(
    db: DbSession, shops: ShopProfilePort = Depends(get_shop_profile),
) -> SubmitPublicConsentUseCase:
    return SubmitPublicConsentInteractor(
        forms=build_consent_form_repository(db), customers=build_customer_repository(db),
        pets=build_pet_repository(db), signatures=build_consent_signature_repository(db), shops=shops,
        limiter=build_public_form_limiter(), now=utc_now, source=build_consent_source(db), link_key=REPORT_LINK_KEY,
    )
