from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.unmark_pet_passed_away_use_case import UnmarkPetPassedAwayUseCase
from customer.app.use_cases.unmark_pet_passed_away_interactor import UnmarkPetPassedAwayInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_unmark_pet_passed_away_use_case(db: DbSession) -> UnmarkPetPassedAwayUseCase:
    return UnmarkPetPassedAwayInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today,
    )
