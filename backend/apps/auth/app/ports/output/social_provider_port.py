from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile


class SocialProviderPort(ABC):
    @abstractmethod
    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        """제공자에게 직접 확인한 신원을 돌려준다. 확인할 수 없으면 ProviderVerificationError."""

    @abstractmethod
    async def revoke(self, identity: IdentityRevocation) -> None:
        """제공자 쪽에서 우리 앱과의 연결을 끊는다. 끊지 못하면 ProviderRevokeError.

        서버가 할 일이 없는 제공자(구글, dev)는 아무것도 하지 않는다.
        """
