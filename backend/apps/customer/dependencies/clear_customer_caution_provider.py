from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.clear_customer_caution_use_case import ClearCustomerCautionUseCase
from customer.app.use_cases.clear_customer_caution_interactor import ClearCustomerCautionInteractor
from customer.dependencies.customer_wiring import build_customer_repository, build_pet_repository
from customer.domain.services.pet_age import seoul_today


def get_clear_customer_caution_use_case(db: DbSession) -> ClearCustomerCautionUseCase:
    return ClearCustomerCautionInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
    )
