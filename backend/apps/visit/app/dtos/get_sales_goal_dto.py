from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetSalesGoalQuery:
    ctx: ShopContext


@dataclass(frozen=True)
class SalesGoalView:
    """매장의 월 목표. 목표가 없으면 monthly_amount 가 None 이다."""

    monthly_amount: int | None
