from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class IssueConsentFormCommand:
    ctx: ShopContext
    pet_ids: tuple[int, ...]
    for_date: date | None = None   # 예약 날 — 그날에 유효한 동의를 받는다. 없으면 오늘
