from __future__ import annotations

from auth.app.dtos.logout_dto import LogoutCommand
from auth.app.ports.input.logout_use_case import LogoutUseCase
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort


class LogoutInteractor(LogoutUseCase):
    """이 기기의 세션만 끊는다. 액세스 토큰은 15분 뒤 저절로 만료된다."""

    def __init__(self, store: RefreshTokenStorePort) -> None:
        self._store = store

    async def logout(self, command: LogoutCommand) -> None:
        await self._store.revoke(command.refresh_token)
