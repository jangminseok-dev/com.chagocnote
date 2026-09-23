from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class RegisterVisitCommand:
    """반려동물 N마리 → 방문 N개. pet_ids 가 비면 보호자만의 방문 하나.

    walk_in 이면 예약 없이 온 손님이다 — starts_at 은 받지 않고 지금(10분 단위 내림)으로, 미용 중으로 만든다.
    duration_minutes 가 없으면 고른 메뉴의 기본 소요 합, 메뉴도 없으면 매장 기본 소요.
    """

    ctx: ShopContext
    customer_id: int
    pet_ids: tuple[int, ...]
    starts_at: datetime | None
    duration_minutes: int | None
    menu_ids: tuple[int, ...]
    memo: str | None
    walk_in: bool


@dataclass(frozen=True)
class RegisteredVisitsView:
    visits: list[VisitView]
    warnings: list[str]   # overlap · closed_day · outside_hours — 막지 않는 경고
