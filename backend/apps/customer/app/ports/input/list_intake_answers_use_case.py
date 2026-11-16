from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.intake_answer_view_dto import IntakeAnswerView
from customer.app.dtos.list_intake_answers_dto import ListIntakeAnswersQuery


class ListIntakeAnswersUseCase(ABC):
    @abstractmethod
    async def list_intake_answers(self, query: ListIntakeAnswersQuery) -> list[IntakeAnswerView]: ...
