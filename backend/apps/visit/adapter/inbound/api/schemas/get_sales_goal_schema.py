from __future__ import annotations

from pydantic import BaseModel

from visit.app.dtos.get_sales_goal_dto import SalesGoalView


class SalesGoalSchema(BaseModel):
    """매장의 월 목표 금액(원). 목표가 없으면 null 이다."""

    monthly_amount: int | None

    @classmethod
    def of(cls, view: SalesGoalView) -> "SalesGoalSchema":
        return cls(monthly_amount=view.monthly_amount)
