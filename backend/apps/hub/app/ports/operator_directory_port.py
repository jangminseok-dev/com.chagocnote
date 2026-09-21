from __future__ import annotations

from abc import ABC, abstractmethod


class OperatorDirectoryPort(ABC):
    """구현: auth. 사용: platform_admin."""

    @abstractmethod
    async def is_operator(self, user_id: int) -> bool:
        """플랫폼 운영자로 지정된 유저인가."""
