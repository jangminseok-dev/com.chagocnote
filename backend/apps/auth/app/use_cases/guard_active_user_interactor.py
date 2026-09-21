from __future__ import annotations

from auth.app.ports.output.user_repository import UserRepository
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort


class GuardActiveUserInteractor(ActiveUserGuardPort):
    """허브의 ActiveUserGuardPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def lock_active(self, user_id: int) -> bool:
        user = await self._users.lock(user_id)
        return user is not None and not user.is_deleted and not user.is_suspended
