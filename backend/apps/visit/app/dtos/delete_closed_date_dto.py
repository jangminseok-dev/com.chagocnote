from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class DeleteClosedDateCommand:
    ctx: ShopContext
    day: date
