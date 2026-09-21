from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


class UserRepository(ABC):
    @abstractmethod
    async def find_by_identity(self, provider: Provider, provider_user_id: str) -> User | None: ...

    @abstractmethod
    async def create_with_identity(self, profile: SocialProfile) -> User:
        """그 신원이 이미 있으면 IdentityAlreadyLinkedError (동시에 온 다른 요청이 먼저 만들었다)."""

    @abstractmethod
    async def fill_provider_refresh_token(
        self, provider: Provider, provider_user_id: str, token: str
    ) -> None:
        """저장된 값이 비어 있을 때만 채운다. 이미 있으면 덮어쓰지 않는다."""

    @abstractmethod
    async def get(self, user_id: int) -> User | None: ...

    @abstractmethod
    async def list_identities(self, user_id: int) -> list[SocialIdentity]: ...

    @abstractmethod
    async def list_by_ids(self, user_ids: Sequence[int]) -> list[User]: ...
