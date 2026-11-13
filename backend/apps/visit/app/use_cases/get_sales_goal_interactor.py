from __future__ import annotations

from visit.app.dtos.get_sales_goal_dto import GetSalesGoalQuery, SalesGoalView
from visit.app.ports.input.get_sales_goal_use_case import GetSalesGoalUseCase
from visit.app.ports.output.sales_goal_repository import SalesGoalRepository


class GetSalesGoalInteractor(GetSalesGoalUseCase):
    """매장의 월 목표를 읽는다. 설정 행을 만들지 않는다."""

    def __init__(self, goals: SalesGoalRepository) -> None:
        self._goals = goals

    async def get_sales_goal(self, query: GetSalesGoalQuery) -> SalesGoalView:
        return SalesGoalView(monthly_amount=await self._goals.get(query.ctx))
