from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetConsentDocumentQuery:
    ctx: ShopContext
    pet_ids: tuple[int, ...]
