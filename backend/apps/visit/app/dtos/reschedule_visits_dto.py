from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class RescheduleVisitsCommand:
    """같은 보호자의 예약 여러 개(가족 묶음)를 한 시각으로 함께 옮긴다. 전부 되거나 전부 안 된다."""

    ctx: ShopContext
    visit_ids: tuple[int, ...]
    starts_at: datetime


@dataclass(frozen=True)
class RescheduledVisitsView:
    visits: list[VisitView]
    warnings: list[str]
