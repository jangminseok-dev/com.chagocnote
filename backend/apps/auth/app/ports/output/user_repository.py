from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


class UserRepository(ABC):
    @abstractmethod
    async def find_by_identity(self, provider: Provider, provider_user_id: str) -> User | None: ...

    @abstractmethod
    async def create_with_identity(self, profile: SocialProfile) -> User: ...

    @abstractmethod
    async def get(self, user_id: int) -> User | None: ...

    @abstractmethod
    async def list_identities(self, user_id: int) -> list[SocialIdentity]: ...
