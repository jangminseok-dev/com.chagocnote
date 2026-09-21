from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class CreateInviteCommand:
    ctx: ShopContext


@dataclass(frozen=True)
class CreatedInvite:
    code: str
    role: str
    expires_at: datetime
