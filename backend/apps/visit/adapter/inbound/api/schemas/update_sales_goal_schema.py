from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StrictInt


class UpdateSalesGoalRequestSchema(BaseModel):
    """월 목표 금액(원). 칸은 필수이고, 목표를 지우려면 null 이나 0 을 보낸다. 범위는 기록의 총액과 같다."""

    monthly_amount: Annotated[StrictInt, Field(ge=0, le=100_000_000)] | None
