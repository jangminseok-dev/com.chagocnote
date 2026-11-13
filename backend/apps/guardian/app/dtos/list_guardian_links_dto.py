from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ListGuardianLinksQuery:
    user_id: int


@dataclass(frozen=True)
class GuardianLinkView:
    link_id: int
    shop_name: str
    linked_at: datetime   # 매장 시간대
