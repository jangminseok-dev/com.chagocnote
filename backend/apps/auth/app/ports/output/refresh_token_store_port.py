from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.value_objects.refresh_lookup import RefreshLookup


class RefreshTokenStorePort(ABC):
    @abstractmethod
    async def current_generation(self, user_id: int) -> int:
        """유저의 현재 세대. "모든 세션 폐기"가 일어날 때마다 하나씩 오른다."""

    @abstractmethod
    async def save(self, token: str, user_id: int, generation: int) -> None:
        """generation 은 발급 시점의 세대다. 그 뒤 세대가 오르면 이 토큰은 무효가 된다."""

    @abstractmethod
    async def take(self, token: str) -> RefreshLookup:
        """토큰을 꺼내면서 '사용됨'으로 바꾼다. 같은 토큰은 한 번만 ACTIVE 로 나온다."""

    @abstractmethod
    async def revoke(self, token: str) -> None: ...

    @abstractmethod
    async def revoke_all(self, user_id: int) -> None:
        """세대를 올린다. 이미 발급된 토큰도, 지금 발급 중인 토큰도 모두 무효가 된다."""
