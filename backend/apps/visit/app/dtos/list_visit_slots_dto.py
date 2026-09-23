from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListVisitSlotsQuery:
    """at 이 있으면 그 시각 한 칸만, 없으면 영업시간의 정시 칸마다. exclude 의 방문은 없는 것으로 친다(옮기기)."""

    ctx: ShopContext
    day: date
    duration_minutes: int | None
    at: time | None
    exclude: tuple[int, ...]


@dataclass(frozen=True)
class SlotView:
    starts_at: datetime        # 매장 시간대
    warnings: list[str]


@dataclass(frozen=True)
class VisitSlotsView:
    date: date
    duration_minutes: int
    closed_day: bool
    slots: list[SlotView]
