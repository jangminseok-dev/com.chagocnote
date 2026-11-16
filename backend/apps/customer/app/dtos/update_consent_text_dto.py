from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateConsentTextCommand:
    ctx: ShopContext
    part: str
    body: str | None      # None 이면 기본 글로 되돌린다
