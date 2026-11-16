from __future__ import annotations

from customer.app.dtos.update_intake_questions_dto import UpdateIntakeQuestionsCommand
from customer.app.ports.input.update_intake_questions_use_case import UpdateIntakeQuestionsUseCase
from customer.app.ports.output.intake_question_repository import IntakeQuestionRepository
from customer.domain.entities.intake import IntakeQuestion, QuestionDraft
from customer.domain.services.intake_question_rules import check_questions


class UpdateIntakeQuestionsInteractor(UpdateIntakeQuestionsUseCase):
    """질문의 목록 전체를 바꾼다(⑪ 설계 3.4). 열려 있던 링크는 다음에 열 때 새 구성이다.

    지운 질문의 행은 남는다 — 이미 받은 답이 그 질문을 가리킨다.
    """

    def __init__(self, questions: IntakeQuestionRepository) -> None:
        self._questions = questions

    async def update_intake_questions(self, command: UpdateIntakeQuestionsCommand) -> list[IntakeQuestion]:
        known = frozenset(question.id for question in await self._questions.list_live(command.ctx))
        check_questions(command.questions, known)
        cleaned = tuple(
            QuestionDraft(id=draft.id, label=draft.label.strip(), required=draft.required)
            for draft in command.questions)
        return await self._questions.replace_all(command.ctx, cleaned)
