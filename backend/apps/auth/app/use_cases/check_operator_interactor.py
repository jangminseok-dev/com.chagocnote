from __future__ import annotations

from auth.app.ports.output.operator_repository import OperatorRepository
from hub.app.ports.operator_directory_port import OperatorDirectoryPort


class CheckOperatorInteractor(OperatorDirectoryPort):
    """허브의 OperatorDirectoryPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, operators: OperatorRepository) -> None:
        self._operators = operators

    async def is_operator(self, user_id: int) -> bool:
        return await self._operators.is_operator(user_id)
