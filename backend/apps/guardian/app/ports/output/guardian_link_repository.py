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

    # --- 가족(⑫). 잠금 순서: 유저 행 → 기본 연결 행 → 가족 초대 행 → 가족 연결 행 ---

    @abstractmethod
    async def lock_primary(self, link_id: int) -> GuardianLink | None:
        """살아 있는 기본 연결 행을 잠근다(`FOR UPDATE`). 없거나 끝났거나 가족 연결이면 None."""

    @abstractmethod
    async def lock_primaries(self, link_ids: list[int]) -> list[GuardianLink]:
        """살아 있는 기본 연결 행들을 ID 오름차순으로 잠근다(탈퇴)."""

    @abstractmethod
    async def primaries_reached_by(self, user_id: int) -> list[int]:
        """그 계정이 닿는 살아 있는 기본 연결 — 자기 기본 연결들과 자기 가족 연결의 부모들."""

    @abstractmethod
    async def create_family(self, user_id: int, primary: GuardianLink, now: datetime) -> GuardianLink:
        """기본 연결 아래에 가족 연결을 넣는다. 부르기 전에 기본 연결 행을 잠근다."""

    @abstractmethod
    async def find_family(self, primary_id: int, user_id: int) -> GuardianLink | None:
        """그 계정이 그 기본 연결 아래의 살아 있는 가족이면 그 연결."""

    @abstractmethod
    async def get_family(self, primary_id: int, family_id: int) -> GuardianLink | None:
        """그 기본 연결 아래의 살아 있는 가족 연결 하나. 남의 것이면 None."""

    @abstractmethod
    async def list_family(self, primary_id: int) -> list[GuardianLink]:
        """살아 있는 가족 연결 — 이은 순서."""

    @abstractmethod
    async def family_counts(self, primary_ids: list[int]) -> dict[int, int]:
        """기본 연결마다 살아 있는 가족의 수(없으면 빠진다)."""

    @abstractmethod
    async def end_family(self, primary_ids: list[int], ended_by: str, now: datetime) -> int:
        """그 기본 연결들 아래의 가족 연결을 모두 끝낸다. 부르기 전에 기본 연결 행을 잠근다."""

    @abstractmethod
    async def mark_family_seen(self, primary_id: int, now: datetime) -> None:
        """기본 보호자가 가족 목록을 봤다 — 새로 이은 줄의 알림을 거둔다."""

