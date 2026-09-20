from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.value_objects.refresh_lookup import RefreshLookup


class RefreshTokenStorePort(ABC):
    @abstractmethod
    async def save(self, token: str, user_id: int) -> None: ...

    @abstractmethod
    async def take(self, token: str) -> RefreshLookup:
        """토큰을 꺼내면서 '사용됨'으로 바꾼다. 같은 토큰은 한 번만 ACTIVE 로 나온다."""

    @abstractmethod
    async def revoke(self, token: str) -> None: ...

    @abstractmethod
    async def revoke_all(self, user_id: int) -> None: ...
