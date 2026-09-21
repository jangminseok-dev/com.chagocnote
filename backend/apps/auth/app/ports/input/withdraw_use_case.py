from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.withdraw_dto import WithdrawCommand, WithdrawResult


class WithdrawUseCase(ABC):
    @abstractmethod
    async def withdraw(self, command: WithdrawCommand) -> WithdrawResult: ...
