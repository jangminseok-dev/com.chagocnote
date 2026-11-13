from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext


class SalesGoalRepository(ABC):
    """매장의 월 목표 금액. 일정·알림장 설정과 같은 행(visit_shop_settings)의 칸이다."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> int | None:
        """목표 금액(원). 목표가 없거나 설정 행이 없으면 None. 행을 만들지 않는다."""

    @abstractmethod
    async def put(self, ctx: ShopContext, monthly_amount: int | None) -> int | None:
        """목표를 정하거나(None 이면) 지운다. 설정 행이 이미 있어야 한다(ScheduleRepository.ensure 뒤에 부른다)."""
