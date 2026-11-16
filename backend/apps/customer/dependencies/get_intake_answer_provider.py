from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.get_intake_answer_use_case import GetIntakeAnswerUseCase
from customer.app.use_cases.get_intake_answer_interactor import GetIntakeAnswerInteractor
from customer.dependencies.customer_wiring import (
    build_condition_type_repository, build_customer_repository, build_form_settings_repository,
    build_intake_answer_repository, build_pet_repository, utc_now,
)


def get_get_intake_answer_use_case(db: DbSession) -> GetIntakeAnswerUseCase:
    return GetIntakeAnswerInteractor(
        answers=build_intake_answer_repository(db), settings=build_form_settings_repository(db),
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        condition_types=build_condition_type_repository(db), now=utc_now,
    )
