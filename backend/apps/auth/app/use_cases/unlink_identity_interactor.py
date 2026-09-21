from __future__ import annotations

from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand, UnlinkIdentityResult
from auth.app.ports.input.unlink_identity_use_case import UnlinkIdentityUseCase
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from auth.domain.errors import (
    AccountSuspendedError,
    IdentityNotFoundError,
    UnsupportedProviderError,
    UserNotFoundError,
)
from auth.domain.services.identity_guard import ensure_identity_remains
from auth.domain.value_objects.provider import Provider


class UnlinkIdentityInteractor(UnlinkIdentityUseCase):
    def __init__(
        self, users: UserRepository, store: RefreshTokenStorePort, sessions: SessionIssuer
    ) -> None:
        self._users = users
        self._store = store
        self._sessions = sessions

    async def unlink(self, command: UnlinkIdentityCommand) -> UnlinkIdentityResult:
        try:
            provider = Provider(command.provider)
        except ValueError as exc:
            raise UnsupportedProviderError(f"{command.provider} 로그인은 지원하지 않습니다.") from exc
        # 서로 다른 수단의 해제가 동시에 와서 0개가 되지 않게, 유저 행을 잠근 뒤에 센다.
        user = await self._users.lock(command.user_id)
        if user is None or user.is_deleted:
            raise UserNotFoundError("다시 로그인해 주세요.")
        if user.is_suspended:
            # 요청 시작 때는 정지 전이었어도, 잠금을 얻는 사이 정지가 걸렸을 수 있다. 그대로 진행하면
            # 이 요청이 정지된 유저의 세션을 전부 끊고 새 토큰까지 내주게 된다.
            raise AccountSuspendedError("정지된 계정입니다.")
        revocations = await self._users.list_revocations(user.id)
        target = next((r for r in revocations if r.provider is provider), None)
        if target is None:
            raise IdentityNotFoundError(f"{provider.value} 로그인은 연결되어 있지 않습니다.")
        ensure_identity_remains(len(revocations))
        await self._users.delete_identity(user.id, provider)
        # 해제한 수단으로 만든 세션이 다른 기기에 남지 않게 전부 끊고, 요청한 기기에만 새 토큰을 준다.
        await self._store.revoke_all(user.id)
        tokens = await self._sessions.issue(user.id)
        return UnlinkIdentityResult(
            identities=tuple(r.provider.value for r in revocations if r.provider is not provider),
            tokens=tokens,
            revocation=target,
        )
