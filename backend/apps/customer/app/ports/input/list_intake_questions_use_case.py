from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.list_intake_questions_dto import ListIntakeQuestionsQuery
from customer.domain.entities.intake import IntakeQuestion


class ListIntakeQuestionsUseCase(ABC):
    @abstractmethod
    async def list_intake_questions(self, query: ListIntakeQuestionsQuery) -> list[IntakeQuestion]: ...
