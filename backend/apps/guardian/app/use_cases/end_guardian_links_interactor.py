from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from hub.app.ports.guardian_lifecycle_port import GuardianLifecyclePort


class EndGuardianLinksInteractor(GuardianLifecyclePort):
    """계정 탈퇴(auth)와 고객 익명화(customer)가 부르는 연결 끝내기. 부르는 쪽의 트랜잭션 안에서 돈다 —
    탈퇴는 유저 행을, 익명화는 고객 행을 이미 잠그고 있다(잠금 순서의 끝이 보호자 연결 행이다)."""

    def __init__(
        self, links: GuardianLinkRepository, now: Callable[[], datetime], invites: FamilyInviteRepository | None = None,
    ) -> None:
        self._links = links
        self._now = now
        self._invites = invites

    async def end_for_user(self, user_id: int) -> int:
        """탈퇴 — 그 계정이 닿는 기본 연결 행(자기 것 + 자기 가족 연결의 부모)을 ID 오름차순으로 잠근 뒤,
        자기 기본 연결 아래의 초대·가족을 끝내고 자기 연결(기본·가족)을 모두 끝낸다(⑫)."""
        now = self._now()
        primaries = await self._links.lock_primaries(await self._links.primaries_reached_by(user_id))
        own = [p.id for p in primaries if p.user_id == user_id]
        if self._invites is not None:
            await self._invites.revoke_unused(own, now)
        ended = await self._links.end_family(own, "withdrawn", now)
        return ended + await self._links.end_all_for_user(user_id, now)

    async def end_for_customer(self, shop_id: int, customer_id: int) -> int:
        """익명화 — 기본 연결 행을 잠그고 초대를 죽인 뒤 그 카드의 연결(기본·가족)을 모두 끝낸다."""
        now = self._now()
        link = await self._links.find_live_for_customer(shop_id, customer_id)
        if link is not None and await self._links.lock_primary(link.id) is not None and self._invites is not None:
            await self._invites.revoke_unused([link.id], now)
        return await self._links.end_all_for_customer(shop_id, customer_id, now)
