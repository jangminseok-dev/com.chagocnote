from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.update_intake_questions_use_case import UpdateIntakeQuestionsUseCase
from customer.app.use_cases.update_intake_questions_interactor import UpdateIntakeQuestionsInteractor
from customer.dependencies.customer_wiring import build_intake_question_repository


def get_update_intake_questions_use_case(db: DbSession) -> UpdateIntakeQuestionsUseCase:
    return UpdateIntakeQuestionsInteractor(questions=build_intake_question_repository(db))
