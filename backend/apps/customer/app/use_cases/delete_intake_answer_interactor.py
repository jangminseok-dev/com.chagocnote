from __future__ import annotations

from customer.app.dtos.delete_intake_answer_dto import DeleteIntakeAnswerCommand
from customer.app.ports.input.delete_intake_answer_use_case import DeleteIntakeAnswerUseCase
from customer.app.ports.output.intake_answer_repository import IntakeAnswerRepository
from customer.domain.errors import IntakeAnswerNotFoundError


class DeleteIntakeAnswerInteractor(DeleteIntakeAnswerUseCase):
    """받은 문진표를 등록하지 않고 지운다. 요청 줄(보낸 서류)은 그대로다."""

    def __init__(self, answers: IntakeAnswerRepository) -> None:
        self._answers = answers

    async def delete_intake_answer(self, command: DeleteIntakeAnswerCommand) -> None:
        if not await self._answers.delete(command.ctx, command.answer_id):
            raise IntakeAnswerNotFoundError("받은 문진표를 찾을 수 없습니다.")
