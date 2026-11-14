from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.check_view_dto import CheckView


@dataclass(frozen=True)
class GetVisitChecksQuery:
    """아직 없는 예약의 확인할 것 — 보호자와 고른 아이들, 예약할 날."""

    ctx: ShopContext
    customer_id: int
    pet_ids: tuple[int, ...]   # 비면 보호자만의 예약
    day: date                  # 매장 시간대의 날


@dataclass(frozen=True)
class PetChecksView:
    pet_id: int
    checks: list[CheckView]


@dataclass(frozen=True)
class VisitChecksView:
    customer: list[CheckView]      # 보호자 항목 — 한 번만
    pets: list[PetChecksView]      # 받은 순서대로. 그 보호자의 아이가 아닌 것은 빠진다
