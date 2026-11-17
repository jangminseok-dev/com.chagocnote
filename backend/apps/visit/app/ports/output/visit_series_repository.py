from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit_series import VisitSeries


class VisitSeriesRepository(ABC):
    """반복 예약의 묶음(`visit_series`, ⑭). 모든 메서드가 ShopContext 의 매장으로 거른다."""

    @abstractmethod
    async def create(self, ctx: ShopContext, customer_id: int, interval_weeks: int, member_id: int) -> VisitSeries:
        """묶음 하나를 만든다. 방문을 넣기 전에(고객 행을 잠근 뒤) 부른다."""

    @abstractmethod
    async def get(self, ctx: ShopContext, series_id: int) -> VisitSeries:
        """없거나 다른 매장의 것이면 VisitSeriesNotFoundError."""
