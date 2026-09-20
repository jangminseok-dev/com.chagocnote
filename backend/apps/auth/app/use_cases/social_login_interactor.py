from __future__ import annotations

from auth.app.dtos.social_login_dto import SocialLoginCommand, SocialLoginResult
from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from auth.domain.errors import AccountSuspendedError, UnsupportedProviderError
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
        except ValueError:
            raise UnsupportedProviderError(f"{command.provider} 로그인은 지원하지 않습니다.")
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
            user = await self._users.create_with_identity(profile)
        if user.is_suspended:
            raise AccountSuspendedError("정지된 계정입니다.")
        tokens = await self._sessions.issue(user.id)
        return SocialLoginResult(user_id=user.id, is_new_user=is_new_user, tokens=tokens)
