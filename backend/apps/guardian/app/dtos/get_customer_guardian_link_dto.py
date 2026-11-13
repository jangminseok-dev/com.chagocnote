from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetCustomerGuardianLinkQuery:
    ctx: ShopContext
    customer_id: int


@dataclass(frozen=True)
class CustomerGuardianLinkView:
    """매장이 보는 연결 — 여부와 이은 날뿐이다. 보호자가 누구인지는 담지 않는다."""

    linked: bool
    linked_at: datetime | None   # 매장 시간대
