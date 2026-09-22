from __future__ import annotations

from auth.app.dtos.social_login_dto import SocialLoginCommand, SocialLoginResult
from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from auth.domain.entities.user import User
from auth.domain.errors import (
    AccountSuspendedError,
    IdentityAlreadyLinkedError,
    UnsupportedProviderError,
    UserNotFoundError,
)
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile


class SocialLoginInteractor(SocialLoginUseCase):
    def __init__(
        self, providers: SocialProviderResolverPort, users: UserRepository, sessions: SessionIssuer
    ) -> None:
        self._providers = providers
        self._users = users
        self._sessions = sessions

    async def login(self, command: SocialLoginCommand) -> SocialLoginResult:
        try:
            provider = Provider(command.provider)
        except ValueError as exc:
            raise UnsupportedProviderError(f"{command.provider} 로그인은 지원하지 않습니다.") from exc
        # 제공자 검증은 외부 HTTP 다. 유저 행을 잠그기 전에 끝낸다.
        profile = await self._providers.resolve(provider).verify(
            SocialCredentials(
                token=command.token,
                authorization_code=command.authorization_code,
                nonce=command.nonce,
                display_name=command.display_name,
            )
        )
        # 조회와 발급 사이에 해제·탈퇴가 커밋되면 사라진 수단이 30일 세션을 쥐게 된다. 기존 유저에게
        # 발급하기 전에 유저 행을 잠그고 그 신원이 그대로인지 다시 본다. 어긋났으면 조회를 처음부터
        # 한 번만 다시 한다 — 두 번째에도 어긋나면 다시 로그인하라고 끝낸다(무한 루프 금지).
        for _ in range(2):
            user = await self._users.find_by_identity(profile.provider, profile.provider_user_id)
            if user is None:
                created = await self._create(profile)
                if created is not None:
                    return await self._issue(created.id, is_new_user=True)
                # 같은 신원의 첫 로그인이 동시에 두 번 왔다(C1). 먼저 끝난 쪽이 만든 유저를 다시 찾는다.
                continue
            locked = await self._lock_and_recheck(user.id, profile)
            if locked is None:
                continue
            if locked.is_suspended:
                raise AccountSuspendedError("정지된 계정입니다.")
            if profile.provider_refresh_token:
                # 가입 때 받지 못한 제공자 토큰(Apple)을 채운다. 탈퇴 때 제공자 쪽 연결을 끊는 데 쓴다.
                # 잠근 뒤에 부른다 — 잠금 없이 부르면 이 UPDATE 가 해제가 지운 신원을 기다렸다가
                # 0행으로 끝난 뒤 그대로 세션을 내주게 된다.
                await self._users.fill_provider_refresh_token(
                    profile.provider, profile.provider_user_id, profile.provider_refresh_token
                )
            return await self._issue(locked.id, is_new_user=False)
        raise UserNotFoundError("다시 로그인해 주세요.")

    async def _create(self, profile: SocialProfile) -> User | None:
        """처음 보는 신원이면 유저를 만든다. 동시에 온 다른 요청이 먼저 만들었으면 None (C1).

        방금 만든 행은 이 트랜잭션 밖에서 아직 보이지 않으므로 잠글 것이 없다.
        """
        try:
            return await self._users.create_with_identity(profile)
        except IdentityAlreadyLinkedError:
            return None

    async def _lock_and_recheck(self, user_id: int, profile: SocialProfile) -> User | None:
        """유저 행을 잠그고, 기다리는 사이 그 신원이 사라지거나 다른 유저로 옮겨 가지 않았는지 다시 본다.

        로그인이 잠그는 것은 이 유저 행 하나뿐이고 그 뒤로는 어떤 행도 잠그지 않으므로, 잠금 순서
        (유저 → 매장 → 멤버 → 초대)의 맨 앞만 쓰는 셈이라 다른 경로와 교착하지 않는다.
        어긋났으면 None 을 돌려주어 부르는 쪽이 조회를 처음부터 다시 하게 한다.
        """
        locked = await self._users.lock(user_id)
        current = await self._users.find_by_identity(profile.provider, profile.provider_user_id)
        if locked is None or locked.is_deleted or current is None or current.id != user_id:
            return None
        return locked

    async def _issue(self, user_id: int, is_new_user: bool) -> SocialLoginResult:
        tokens = await self._sessions.issue(user_id, fresh_login=True)
        return SocialLoginResult(user_id=user_id, is_new_user=is_new_user, tokens=tokens)
