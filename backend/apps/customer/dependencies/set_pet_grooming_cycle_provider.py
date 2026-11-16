from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.set_pet_grooming_cycle_use_case import SetPetGroomingCycleUseCase
from customer.app.use_cases.set_pet_grooming_cycle_interactor import SetPetGroomingCycleInteractor
from customer.dependencies.customer_wiring import build_pet_repository


def get_set_pet_grooming_cycle_use_case(db: DbSession) -> SetPetGroomingCycleUseCase:
    return SetPetGroomingCycleInteractor(pets=build_pet_repository(db))
