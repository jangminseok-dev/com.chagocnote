from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.list_intake_answers_use_case import ListIntakeAnswersUseCase
from customer.app.use_cases.list_intake_answers_interactor import ListIntakeAnswersInteractor
from customer.dependencies.customer_wiring import (
    build_condition_type_repository, build_customer_repository, build_form_settings_repository,
    build_intake_answer_repository, build_pet_repository, utc_now,
)


def get_list_intake_answers_use_case(db: DbSession) -> ListIntakeAnswersUseCase:
    return ListIntakeAnswersInteractor(
        answers=build_intake_answer_repository(db), settings=build_form_settings_repository(db),
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        condition_types=build_condition_type_repository(db), now=utc_now,
    )
