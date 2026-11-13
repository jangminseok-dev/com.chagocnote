from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_sales_goal_dto import GetSalesGoalQuery, SalesGoalView


class GetSalesGoalUseCase(ABC):
    @abstractmethod
    async def get_sales_goal(self, query: GetSalesGoalQuery) -> SalesGoalView: ...
