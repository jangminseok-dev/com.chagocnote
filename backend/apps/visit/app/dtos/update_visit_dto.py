from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class UpdateVisitCommand:
    """방문 하나를 통째로 바꾼다(PUT). 날짜·시간·반려동물은 예약됨일 때만, 반려동물은 같은 보호자의 아이로만
    바꿀 수 있다. 메뉴·소요·메모는 미용 중·완료일 때도 바꾼다(실제로 한 메뉴를 ④ 기록이 쓴다)."""

    ctx: ShopContext
    visit_id: int
    starts_at: datetime
    pet_id: int | None
    duration_minutes: int
    menu_ids: tuple[int, ...]
    memo: str | None


@dataclass(frozen=True)
class UpdatedVisitView:
    visit: VisitView
    warnings: list[str]
