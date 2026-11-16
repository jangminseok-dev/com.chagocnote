from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.update_intake_questions_dto import UpdateIntakeQuestionsCommand
from customer.domain.entities.intake import IntakeQuestion


class UpdateIntakeQuestionsUseCase(ABC):
    @abstractmethod
    async def update_intake_questions(self, command: UpdateIntakeQuestionsCommand) -> list[IntakeQuestion]: ...
