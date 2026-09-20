from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile


class SocialProviderPort(ABC):
    @abstractmethod
    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        """제공자에게 직접 확인한 신원을 돌려준다. 확인할 수 없으면 ProviderVerificationError."""
