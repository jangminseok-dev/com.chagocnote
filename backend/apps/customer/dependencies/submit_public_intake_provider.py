from __future__ import annotations

from fastapi import Depends

from core.config import REPORT_LINK_KEY
from core.database import DbSession
from customer.app.ports.input.submit_public_intake_use_case import SubmitPublicIntakeUseCase
from customer.app.use_cases.submit_public_intake_interactor import SubmitPublicIntakeInteractor
from customer.dependencies.customer_wiring import (
    build_consent_signature_repository, build_customer_repository, build_intake_answer_repository, build_intake_form_repository, build_intake_reader,
    build_public_form_limiter, utc_now,
)
from customer.dependencies.hub_ports import get_shop_profile
from hub.app.ports.shop_profile_port import ShopProfilePort


def get_submit_public_intake_use_case(
    db: DbSession, shops: ShopProfilePort = Depends(get_shop_profile),
) -> SubmitPublicIntakeUseCase:
    return SubmitPublicIntakeInteractor(
        forms=build_intake_form_repository(db), answers=build_intake_answer_repository(db),
        customers=build_customer_repository(db), reader=build_intake_reader(db), shops=shops,
        limiter=build_public_form_limiter(), now=utc_now, link_key=REPORT_LINK_KEY,
        signatures=build_consent_signature_repository(db),
    )
