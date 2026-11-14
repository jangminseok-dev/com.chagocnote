from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class EnqueueReindexCommand:
    ctx: ShopContext
    scope: str       # visit · pet · customer
    ref_id: int
