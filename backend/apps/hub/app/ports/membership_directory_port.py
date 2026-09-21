from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.membership_summary import MembershipSummary


class MembershipDirectoryPort(ABC):
    """구현: tenancy. 사용: auth (GET /v1/me)."""

    @abstractmethod
    async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
        """유저가 지금 속해 있는 매장들. 내보내진 소속과 닫힌 매장은 빠진다."""
