from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class SignConsentInShopCommand:
    ctx: ShopContext
    pet_ids: tuple[int, ...]
    doc_digest: str
    signer_name: str
    signature_png: bytes
    for_date: date | None = None
