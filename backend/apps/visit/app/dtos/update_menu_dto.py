from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateMenuCommand:
    ctx: ShopContext
    menu_id: int
    name: str
    default_duration_minutes: int | None
    sort_order: int
