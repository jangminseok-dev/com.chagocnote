from __future__ import annotations

from customer.app.dtos.list_intake_questions_dto import ListIntakeQuestionsQuery
from customer.app.ports.input.list_intake_questions_use_case import ListIntakeQuestionsUseCase
from customer.app.ports.output.intake_question_repository import IntakeQuestionRepository
from customer.domain.entities.intake import IntakeQuestion


class ListIntakeQuestionsInteractor(ListIntakeQuestionsUseCase):
    """매장이 문진표에 더한 질문. 더한 적이 없으면 비어 있다 — 기본 칸만으로 돈다."""

    def __init__(self, questions: IntakeQuestionRepository) -> None:
        self._questions = questions

    async def list_intake_questions(self, query: ListIntakeQuestionsQuery) -> list[IntakeQuestion]:
        return await self._questions.list_live(query.ctx)
