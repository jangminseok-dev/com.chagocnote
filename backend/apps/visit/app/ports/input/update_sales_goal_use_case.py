from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_sales_goal_dto import SalesGoalView
from visit.app.dtos.update_sales_goal_dto import UpdateSalesGoalCommand


class UpdateSalesGoalUseCase(ABC):
    @abstractmethod
    async def update_sales_goal(self, command: UpdateSalesGoalCommand) -> SalesGoalView: ...
