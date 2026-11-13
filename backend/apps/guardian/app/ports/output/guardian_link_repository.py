from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from guardian.domain.entities.guardian_link import GuardianLink


class GuardianLinkRepository(ABC):
    """보호자 연결(guardian_links). **`ShopContext` 를 받지 않는다** — 보호자는 매장의 멤버가 아니라 매장 컨텍스트가
    없고, 범위는 계정(user_id)이다. 매장 쪽 유스케이스는 가드가 준 `ShopContext` 의 shop_id 를 넘긴다.
    이 스포크는 고객·반려동물을 읽지 않는다(매장 범위 포트를 부를 컨텍스트를 만들지 않는다).
    """

    @abstractmethod
    async def create(
        self, user_id: int, shop_id: int, customer_id: int, verified_by: str, now: datetime
    ) -> GuardianLink:
        """새 연결을 넣는다. 그 고객 카드에 살아 있는 연결이 있으면 GuardianAlreadyLinkedError —
        세이브포인트 안에서 넣으므로 트랜잭션은 계속 쓸 수 있다(동시에 온 둘째도 여기서 걸린다)."""

    @abstractmethod
    async def find_live_for_customer(self, shop_id: int, customer_id: int) -> GuardianLink | None: ...

    @abstractmethod
    async def get_live(self, user_id: int, link_id: int) -> GuardianLink | None:
        """그 계정의 살아 있는 연결. 없거나 남의 것이거나 끝났으면 None."""

    @abstractmethod
    async def list_live_for_user(self, user_id: int) -> list[GuardianLink]:
        """이은 순(created_at, id)."""

    @abstractmethod
    async def end(self, link_id: int, ended_by: str, now: datetime) -> bool:
        """살아 있을 때만 끝낸다. 끝냈으면 True."""

    @abstractmethod
    async def end_all_for_user(self, user_id: int, now: datetime) -> int:
        """계정 탈퇴 — 그 계정의 살아 있는 연결을 모두 withdrawn 으로 끝낸다. 끝낸 수."""

    @abstractmethod
    async def end_all_for_customer(self, shop_id: int, customer_id: int, now: datetime) -> int:
        """고객 익명화 — 그 고객 카드의 살아 있는 연결을 anonymized 로 끝낸다. 끝낸 수."""
