from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class IssueIntakeFormCommand:
    """문진표를 보낼 곳. 둘 다 없으면 새 손님, 고객만 있으면 그 고객의 새 아이, 아이가 있으면 그 아이의 정보를 다시 받는다."""

    ctx: ShopContext
    customer_id: int | None = None
    pet_id: int | None = None
