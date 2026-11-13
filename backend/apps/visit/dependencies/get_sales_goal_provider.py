from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_sales_goal_use_case import GetSalesGoalUseCase
from visit.app.use_cases.get_sales_goal_interactor import GetSalesGoalInteractor
from visit.dependencies.visit_wiring import build_sales_goal_repository


def get_get_sales_goal_use_case(db: DbSession) -> GetSalesGoalUseCase:
    return GetSalesGoalInteractor(goals=build_sales_goal_repository(db))
