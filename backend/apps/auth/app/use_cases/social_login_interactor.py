from __future__ import annotations

from auth.app.dtos.social_login_dto import SocialLoginCommand, SocialLoginResult
from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from auth.domain.errors import (
    AccountSuspendedError,
    IdentityAlreadyLinkedError,
    UnsupportedProviderError,
)
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials


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
        profile = await self._providers.resolve(provider).verify(
            SocialCredentials(
                token=command.token,
                authorization_code=command.authorization_code,
                nonce=command.nonce,
                display_name=command.display_name,
            )
        )
        user = await self._users.find_by_identity(profile.provider, profile.provider_user_id)
        is_new_user = user is None
        if user is None:
            try:
                user = await self._users.create_with_identity(profile)
            except IdentityAlreadyLinkedError:
                # 같은 신원의 첫 로그인이 동시에 두 번 왔다. 먼저 끝난 쪽이 만든 유저로 로그인한다.
                user = await self._users.find_by_identity(profile.provider, profile.provider_user_id)
                is_new_user = False
        elif profile.provider_refresh_token:
            # 가입 때 받지 못한 제공자 토큰(Apple)을 채운다. 탈퇴 때 제공자 쪽 연결을 끊는 데 쓴다.
            await self._users.fill_provider_refresh_token(
                profile.provider, profile.provider_user_id, profile.provider_refresh_token
            )
        if user.is_suspended:
            raise AccountSuspendedError("정지된 계정입니다.")
        tokens = await self._sessions.issue(user.id)
        return SocialLoginResult(user_id=user.id, is_new_user=is_new_user, tokens=tokens)
