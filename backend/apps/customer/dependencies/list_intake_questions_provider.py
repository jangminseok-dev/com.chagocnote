from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.list_intake_questions_use_case import ListIntakeQuestionsUseCase
from customer.app.use_cases.list_intake_questions_interactor import ListIntakeQuestionsInteractor
from customer.dependencies.customer_wiring import build_intake_question_repository


def get_list_intake_questions_use_case(db: DbSession) -> ListIntakeQuestionsUseCase:
    return ListIntakeQuestionsInteractor(questions=build_intake_question_repository(db))
