from __future__ import annotations

from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.dtos.token_dto import TokenPair
from auth.app.ports.input.refresh_token_use_case import RefreshTokenUseCase
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from auth.domain.errors import (
    AccountSuspendedError,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
)
from auth.domain.value_objects.refresh_lookup import RefreshStatus


class RefreshTokenInteractor(RefreshTokenUseCase):
    def __init__(
        self, store: RefreshTokenStorePort, users: UserRepository, sessions: SessionIssuer
    ) -> None:
        self._store = store
        self._users = users
        self._sessions = sessions

    async def refresh(self, command: RefreshTokenCommand) -> TokenPair:
        lookup = await self._store.take(command.refresh_token)
        if lookup.status is RefreshStatus.USED and lookup.user_id is not None:
            # 이미 새 토큰으로 바뀐 토큰이 다시 왔다 — 탈취로 보고 모든 세션을 끊는다.
            await self._store.revoke_all(lookup.user_id)
            raise RefreshTokenReuseError("다시 로그인해 주세요.")
        if lookup.status is not RefreshStatus.ACTIVE or lookup.user_id is None:
            raise InvalidRefreshTokenError("다시 로그인해 주세요.")
        user = await self._users.get(lookup.user_id)
        if user is None or user.is_deleted:
            raise InvalidRefreshTokenError("다시 로그인해 주세요.")
        if user.is_suspended:
            raise AccountSuspendedError("정지된 계정입니다.")
        return await self._sessions.issue(user.id, lookup.generation)
