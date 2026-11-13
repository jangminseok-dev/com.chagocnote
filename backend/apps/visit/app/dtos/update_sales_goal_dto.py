from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateSalesGoalCommand:
    """월 목표를 정한다. monthly_amount 가 None 이거나 0 이면 목표를 지운다."""

    ctx: ShopContext
    monthly_amount: int | None
