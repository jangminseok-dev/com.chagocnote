from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListVisitNotificationsQuery:
    ctx: ShopContext
    visit_id: int
