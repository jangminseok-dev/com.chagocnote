from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.delete_intake_answer_use_case import DeleteIntakeAnswerUseCase
from customer.app.use_cases.delete_intake_answer_interactor import DeleteIntakeAnswerInteractor
from customer.dependencies.customer_wiring import build_intake_answer_repository


def get_delete_intake_answer_use_case(db: DbSession) -> DeleteIntakeAnswerUseCase:
    return DeleteIntakeAnswerInteractor(answers=build_intake_answer_repository(db))
