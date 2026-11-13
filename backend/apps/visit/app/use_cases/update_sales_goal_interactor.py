from __future__ import annotations

from visit.app.dtos.get_sales_goal_dto import SalesGoalView
from visit.app.dtos.update_sales_goal_dto import UpdateSalesGoalCommand
from visit.app.ports.input.update_sales_goal_use_case import UpdateSalesGoalUseCase
from visit.app.ports.output.sales_goal_repository import SalesGoalRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository


class UpdateSalesGoalInteractor(UpdateSalesGoalUseCase):
    """월 목표를 정하거나 지운다. 0 은 '목표 없음'이다."""

    def __init__(self, schedule: ScheduleRepository, goals: SalesGoalRepository) -> None:
        self._schedule = schedule
        self._goals = goals

    async def update_sales_goal(self, command: UpdateSalesGoalCommand) -> SalesGoalView:
        await self._schedule.ensure(command.ctx)   # 설정 행은 일정 설정과 함께 쓴다 — 없으면 여기서 생긴다
        saved = await self._goals.put(command.ctx, command.monthly_amount or None)
        return SalesGoalView(monthly_amount=saved)
