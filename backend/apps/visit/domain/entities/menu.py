from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Menu:
    """매장 메뉴 하나. 지우지 않고 보관한다 — 지난 방문이 가리키고 있다."""

    id: int
    shop_id: int
    name: str
    default_duration_minutes: int | None   # None 이면 매장 기본 소요
    sort_order: int
    archived_at: datetime | None
    price: int | None   # 정가(원). None 이면 가격 미정 — 기록의 금액을 미리 채울 때만 쓴다

    @property
    def archived(self) -> bool:
        return self.archived_at is not None
