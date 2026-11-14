from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class SetPetGroomingConsentCommand:
    ctx: ShopContext
    pet_id: int
    received_on: date | None   # None 이면 오늘
