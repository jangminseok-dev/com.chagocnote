from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.mark_pet_revisit_nudged_use_case import MarkPetRevisitNudgedUseCase
from customer.app.use_cases.mark_pet_revisit_nudged_interactor import MarkPetRevisitNudgedInteractor
from customer.dependencies.customer_wiring import build_pet_repository
from customer.domain.services.pet_age import seoul_today


def get_mark_pet_revisit_nudged_use_case(db: DbSession) -> MarkPetRevisitNudgedUseCase:
    return MarkPetRevisitNudgedInteractor(pets=build_pet_repository(db), today=seoul_today)
