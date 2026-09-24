from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit_record import VisitRecord


class VisitRecordRepository(ABC):
    """미용 기록(visit_records 와 항목·미디어 두 하위 표). 읽기는 방문의 매장(ShopContext)으로 거른다.

    쓰기는 방문 행을 잠근 **뒤에만** 부른다 — 방문이 이 매장의 것임은 잠금(`lock_visits`)이 이미 확인했다.
    """

    @abstractmethod
    async def get(self, ctx: ShopContext, visit_id: int) -> VisitRecord | None:
        """없거나 다른 매장의 방문이면 None."""

    @abstractmethod
    async def save(self, ctx: ShopContext, record: VisitRecord) -> VisitRecord:
        """행이 없으면 넣고 있으면 바꾼다. 항목·미디어는 통째로 바꾼다. 버전은 부르는 쪽이 정해 넘긴다."""
