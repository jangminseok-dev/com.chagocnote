from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
from customer.app.use_cases.mark_pet_passed_away_interactor import MarkPetPassedAwayInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_mark_pet_passed_away_use_case(db: DbSession) -> MarkPetPassedAwayUseCase:
    return MarkPetPassedAwayInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today,
    )
