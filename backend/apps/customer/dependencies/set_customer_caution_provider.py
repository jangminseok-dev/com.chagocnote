from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.set_customer_caution_use_case import SetCustomerCautionUseCase
from customer.app.use_cases.set_customer_caution_interactor import SetCustomerCautionInteractor
from customer.dependencies.customer_wiring import build_customer_repository, build_pet_repository
from customer.domain.services.pet_age import seoul_today


def get_set_customer_caution_use_case(db: DbSession) -> SetCustomerCautionUseCase:
    return SetCustomerCautionInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
    )
