from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from hub.app.dtos.user_profile import UserProfile


class UserDirectoryPort(ABC):
    """구현: auth. 사용: tenancy."""

    @abstractmethod
    async def get_profiles(self, user_ids: Sequence[int]) -> dict[int, UserProfile]:
        """유저 ID → 프로필. 한 번에 묶어서 조회한다."""
