from __future__ import annotations

from auth.app.dtos.grant_operator_dto import GrantOperatorCommand
from auth.app.ports.input.grant_operator_use_case import GrantOperatorUseCase
from auth.app.ports.output.operator_repository import OperatorRepository
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.errors import UserNotFoundError


class GrantOperatorInteractor(GrantOperatorUseCase):
    """HTTP 표면이 없다. scripts/grant_operator.py 가 부른다."""

    def __init__(self, users: UserRepository, operators: OperatorRepository) -> None:
        self._users = users
        self._operators = operators

    async def grant(self, command: GrantOperatorCommand) -> None:
        user = await self._users.get(command.user_id)
        if user is None or user.is_deleted:
            raise UserNotFoundError(f"유저 {command.user_id} 을(를) 찾을 수 없습니다.")
        await self._operators.grant(user.id)
