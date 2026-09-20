from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.value_objects.provider import Provider


class SocialProviderResolverPort(ABC):
    @abstractmethod
    def resolve(self, provider: Provider) -> SocialProviderPort:
        """등록되지 않은 제공자면 UnsupportedProviderError."""
