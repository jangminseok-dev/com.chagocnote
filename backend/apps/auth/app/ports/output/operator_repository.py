from __future__ import annotations

from abc import ABC, abstractmethod


class OperatorRepository(ABC):
    @abstractmethod
    async def is_operator(self, user_id: int) -> bool: ...

    @abstractmethod
    async def grant(self, user_id: int) -> None:
        """여러 번 불러도 결과가 같다."""

    @abstractmethod
    async def revoke(self, user_id: int) -> None:
        """여러 번 불러도 결과가 같다."""
