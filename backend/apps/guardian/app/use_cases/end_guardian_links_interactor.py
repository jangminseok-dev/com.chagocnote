from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from hub.app.ports.guardian_lifecycle_port import GuardianLifecyclePort


class EndGuardianLinksInteractor(GuardianLifecyclePort):
    """계정 탈퇴(auth)와 고객 익명화(customer)가 부르는 연결 끝내기. 부르는 쪽의 트랜잭션 안에서 돈다 —
    탈퇴는 유저 행을, 익명화는 고객 행을 이미 잠그고 있다(잠금 순서의 끝이 보호자 연결 행이다)."""

    def __init__(self, links: GuardianLinkRepository, now: Callable[[], datetime]) -> None:
        self._links = links
        self._now = now

    async def end_for_user(self, user_id: int) -> int:
        return await self._links.end_all_for_user(user_id, self._now())

    async def end_for_customer(self, shop_id: int, customer_id: int) -> int:
        return await self._links.end_all_for_customer(shop_id, customer_id, self._now())
