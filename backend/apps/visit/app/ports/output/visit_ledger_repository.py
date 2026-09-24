from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


class VisitLedgerRepository(ABC):
    """고객 쪽이 묻는 원장 — 방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기. 모든 메서드가 ShopContext 의 매장으로 거른다.

    허브 포트 `VisitLedgerPort` 구현(`visit_ledger_interactor`)과 방문 상세의 노쇼 횟수가 받는다.
    """

    @abstractmethod
    async def pet_has_visits(self, ctx: ShopContext, pet_id: int, active_only: bool) -> bool: ...

    @abstractmethod
    async def customer_has_active(self, ctx: ShopContext, customer_id: int) -> bool: ...

    @abstractmethod
    async def list_active_from(
        self, ctx: ShopContext, customer_id: int, since: datetime, limit: int
    ) -> list[Visit]:
        """since 이후에 시작하는 살아 있는 방문, 시작 순으로 limit 개."""

    @abstractmethod
    async def clear_memos(self, ctx: ShopContext, customer_id: int) -> None: ...

    @abstractmethod
    async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int: ...
