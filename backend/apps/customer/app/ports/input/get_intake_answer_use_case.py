from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.get_intake_answer_dto import GetIntakeAnswerQuery
from customer.app.dtos.intake_answer_view_dto import IntakeAnswerView


class GetIntakeAnswerUseCase(ABC):
    @abstractmethod
    async def get_intake_answer(self, query: GetIntakeAnswerQuery) -> IntakeAnswerView: ...
