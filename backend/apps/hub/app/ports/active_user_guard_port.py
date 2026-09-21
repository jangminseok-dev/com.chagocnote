from __future__ import annotations

from abc import ABC, abstractmethod


class ActiveUserGuardPort(ABC):
    """구현: auth. 사용: tenancy (초대 수락)."""

    @abstractmethod
    async def lock_active(self, user_id: int) -> bool:
        """유저 행을 잠그고, 지금 활동할 수 있는 유저(있고, 탈퇴하지 않았고, 정지되지 않은)인지 돌려준다.

        잠금은 부르는 쪽의 트랜잭션이 끝날 때 풀린다. 같은 유저의 회원 탈퇴와 겹치지 않게 하려는 것이다 —
        소속을 새로 만드는 유스케이스는 매장 행을 잠그기 **전에** 이것을 부른다 (잠금 순서: 유저 → 매장).
        """
