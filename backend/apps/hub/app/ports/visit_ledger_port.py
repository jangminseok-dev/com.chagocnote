from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.upcoming_visit import UpcomingVisit


class VisitLedgerPort(ABC):
    """구현: visit. 사용: customer (반려동물 삭제·무지개다리·고객 익명화의 규칙, 고객 상세, 반려동물 프로필 사진).

    '앞으로의 예약'은 예약됨·미용 중인 방문이다 — 날짜가 지났어도 정리하지 않았으면 여기에 든다.
    customer 는 고객 행을 잠근 **뒤에** 부른다(잠금 순서: 고객 행 → 방문 행). 방문을 쓰는 visit 유스케이스도
    같은 고객 행을 먼저 잠그므로, 확인과 쓰기 사이에 예약이 새로 생기지 않는다.
    """

    @abstractmethod
    async def pet_has_visits(self, ctx: ShopContext, pet_id: int) -> bool:
        """상태와 상관없이 방문이 하나라도 있는가(취소 포함)."""

    @abstractmethod
    async def pet_has_upcoming(self, ctx: ShopContext, pet_id: int) -> bool: ...

    @abstractmethod
    async def customer_has_upcoming(self, ctx: ShopContext, customer_id: int) -> bool: ...

    @abstractmethod
    async def no_show_count(self, ctx: ShopContext, customer_id: int) -> int: ...

    @abstractmethod
    async def upcoming_for_customer(self, ctx: ShopContext, customer_id: int, limit: int) -> list[UpcomingVisit]:
        """오늘(매장 시간대) 이후에 시작하는 앞으로의 예약, 시작 순으로 limit 개."""

    @abstractmethod
    async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
        """그 고객 방문들의 메모와 미용 기록의 두 메모(케어·내부)를 비우고, 그 방문들의 알림장 링크를 끊는다 —
        익명화 때 메모에 남은 개인정보를 지우고(V11, 설계 6.4) 보호자에게 보낸 페이지를 닫는다. 사진은 매장의
        미용 기록이라 남긴다. 부르는 쪽의 트랜잭션 안에서 한다."""

    @abstractmethod
    async def latest_covers(self, ctx: ShopContext, pet_ids: list[int]) -> dict[int, int]:
        """{반려동물 ID: 대표 사진의 media_id} — 사진·영상이 붙은 가장 최근 완료 방문의 대표(후 → 전 → 영상).
        그런 방문이 없는 아이는 빠진다. 반려동물 프로필 사진의 원본이다(설계 8절). 한 번에 묻는다(N+1 없음)."""
