from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit
from visit.domain.value_objects.new_visit import NewVisit


class VisitRepository(ABC):
    """방문. 모든 메서드가 ShopContext 의 매장으로 거른다."""

    @abstractmethod
    async def create_many(self, ctx: ShopContext, visits: list[NewVisit]) -> list[Visit]:
        """한 번에 넣는다. 같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있으면
        VisitDuplicateError — 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""

    @abstractmethod
    async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        """[start, end) 와 시간이 겹치는 살아 있는 방문(예약됨·미용 중)."""
