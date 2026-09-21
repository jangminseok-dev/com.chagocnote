from __future__ import annotations

from auth.app.dtos.link_identity_dto import LinkedIdentities, LinkIdentityCommand
from auth.app.ports.input.link_identity_use_case import LinkIdentityUseCase
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.errors import UnsupportedProviderError, UserNotFoundError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials


class LinkIdentityInteractor(LinkIdentityUseCase):
    def __init__(self, providers: SocialProviderResolverPort, users: UserRepository) -> None:
        self._providers = providers
        self._users = users

    async def link(self, command: LinkIdentityCommand) -> LinkedIdentities:
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
            )
        )
        # 같은 유저의 해제·탈퇴와 겹치지 않게 잠그고, 그 사이 탈퇴했는지 다시 본다.
        user = await self._users.lock(command.user_id)
        if user is None or user.is_deleted:
            raise UserNotFoundError("다시 로그인해 주세요.")
        await self._users.add_identity(user.id, profile)
        identities = await self._users.list_identities(user.id)
        return LinkedIdentities(identities=tuple(i.provider.value for i in identities))
