from __future__ import annotations

from abc import ABC, abstractmethod


class InviteAttemptLimiterPort(ABC):
    @abstractmethod
    async def hit(self, user_id: int) -> int:
        """초대 코드 입력 시도를 하나 세고, 이번 1분 창에서 몇 번째 시도인지 돌려준다."""
