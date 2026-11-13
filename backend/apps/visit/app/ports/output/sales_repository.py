from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Literal

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.sales import (
    DaySales,
    DuePet,
    MenuSales,
    PetVisits,
    RemainingBookings,
    SalesTotals,
    SalesVisitRow,
)

SalesVisitKind = Literal["unrecorded", "no_show", "canceled", "menu"]


class SalesRepository(ABC):
    """매출 집계 — 읽을 때 센다(미리 계산해 둔 표가 없다).

    start·until 은 매장 시간대의 날짜이고 until 은 끝 다음 날이다(start 를 품고 until 은 품지 않는다).
    방문은 시작 시각이 든 날의 것이다. 매출은 완료 방문의 기록에 적힌 총액이다 — 총액이 없는 기록은 세지 않는다.
    """

    @abstractmethod
    async def totals(self, ctx: ShopContext, start: date, until: date) -> SalesTotals: ...

    @abstractmethod
    async def by_day(self, ctx: ShopContext, start: date, until: date) -> list[DaySales]:
        """완료 방문이 있는 날만, 날짜순."""

    @abstractmethod
    async def by_payment(self, ctx: ShopContext, start: date, until: date) -> dict[str | None, int]:
        """결제 수단 → 총액 합. 결제 수단을 고르지 않은 기록은 None 에 모인다. 합은 매출과 같다."""

    @abstractmethod
    async def by_menu(self, ctx: ShopContext, start: date, until: date) -> list[MenuSales]:
        """총액이 있는 기록의 항목만. 금액 큰 순(같으면 메뉴 ID 순)."""

    @abstractmethod
    async def pets(self, ctx: ShopContext, start: date, until: date) -> list[PetVisits]:
        """기간에 완료 방문이 있는 아이들. 마지막 날이 최근인 순(같으면 pet_id 순)."""

    @abstractmethod
    async def remaining_reserved(self, ctx: ShopContext, now: datetime, until: date) -> RemainingBookings:
        """now 부터 until 전까지의 예약(reserved)."""

    @abstractmethod
    async def report_counts(self, ctx: ShopContext, start: date, until: date) -> tuple[int, int]:
        """(알림장을 한 번이라도 만든 완료 방문 수, 그 가운데 보호자가 연 적 있는 방문 수).
        끊었거나 기간이 지난 줄도 보낸 것으로 친다."""

    @abstractmethod
    async def list_visits(
        self, ctx: ShopContext, start: date, until: date, kind: SalesVisitKind, menu_id: int | None,
        before: tuple[datetime, int] | None, limit: int,
    ) -> list[SalesVisitRow]:
        """시작 시각 최신순(같으면 방문 ID 큰 순). before 는 앞 쪽의 마지막 줄(시작 시각, 방문 ID)이다.
        unrecorded — 총액이 없는 완료 방문, menu — 그 메뉴를 항목에 적은(총액이 있는) 완료 방문."""

    @abstractmethod
    async def due_candidates(self, ctx: ShopContext, today: date, now: datetime) -> list[DuePet]:
        """마지막 완료 방문이 57일~365일 전이고 앞으로의 예약(지금 이후의 예약·미용 중)이 없는 아이.
        오래된 순(같으면 pet_id 순). 무지개다리·익명화는 여기서 모른다 — 부르는 쪽이 거른다."""
