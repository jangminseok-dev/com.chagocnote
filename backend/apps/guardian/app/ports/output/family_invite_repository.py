from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from guardian.domain.entities.family_invite import FamilyInvite


class FamilyInviteRepository(ABC):
    """가족 초대(guardian_family_invites, ⑫). 코드 원문은 받지도 저장하지도 않는다 — 해시만."""

    @abstractmethod
    async def create(self, link_id: int, code_hash: str, now: datetime, expires_at: datetime) -> FamilyInvite: ...

    @abstractmethod
    async def find(self, code_hash: str) -> FamilyInvite | None:
        """잠그지 않고 찾는다 — 어느 기본 연결의 초대인지 알아 그 행부터 잠그려고."""

    @abstractmethod
    async def lock(self, invite_id: int) -> FamilyInvite | None:
        """가족 초대 행을 잠근다(기본 연결 행 다음)."""

    @abstractmethod
    async def revoke_unused(self, link_ids: list[int], now: datetime) -> int:
        """그 기본 연결들의 안 쓴 초대를 모두 죽인다."""

    @abstractmethod
    async def mark_used(self, invite_id: int, now: datetime) -> None: ...
