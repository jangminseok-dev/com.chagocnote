from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.delete_intake_answer_dto import DeleteIntakeAnswerCommand


class DeleteIntakeAnswerUseCase(ABC):
    @abstractmethod
    async def delete_intake_answer(self, command: DeleteIntakeAnswerCommand) -> None: ...
