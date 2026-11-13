from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.update_sales_goal_use_case import UpdateSalesGoalUseCase
from visit.app.use_cases.update_sales_goal_interactor import UpdateSalesGoalInteractor
from visit.dependencies.visit_wiring import build_sales_goal_repository, build_schedule_repository


def get_update_sales_goal_use_case(db: DbSession) -> UpdateSalesGoalUseCase:
    return UpdateSalesGoalInteractor(
        schedule=build_schedule_repository(db), goals=build_sales_goal_repository(db)
    )
