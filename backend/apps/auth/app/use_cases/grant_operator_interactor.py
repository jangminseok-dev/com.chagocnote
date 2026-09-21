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
        # 겹친 탈퇴가 이 지정을 지나쳐 가지 않게 유저 행을 잠그고 다시 읽는다 (H4). 잠금 순서는
        # 유저 행이 맨 앞이고, 이 경로는 그 뒤로 운영자 행만 넣으므로 다른 경로와 교착하지 않는다.
        user = await self._users.lock(command.user_id)
        if user is None or user.is_deleted:
            raise UserNotFoundError(f"유저 {command.user_id} 을(를) 찾을 수 없습니다.")
        await self._operators.grant(user.id)
