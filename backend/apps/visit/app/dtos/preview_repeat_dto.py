from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class PreviewRepeatQuery:
    ctx: ShopContext
    customer_id: int
    pet_ids: tuple[int, ...]
    starts_at: datetime            # 첫 회차(시간대가 붙은 시각)
    duration_minutes: int | None   # 없으면 메뉴로 센다(등록과 같다)
    menu_ids: tuple[int, ...]
    interval_weeks: int
    count: int


@dataclass(frozen=True)
class OccurrenceView:
    index: int                # 회차 번호(1 부터) — 등록의 skip 이 이 번호를 쓴다
    starts_at: datetime       # 매장 시간대
    warnings: list[str]       # overlap · closed_day · outside_hours(막지 않는다)
    taken: bool               # 그 아이(아이가 없으면 보호자)에게 그 시각 살아 있는 예약이 이미 있다 — 등록하면 409


@dataclass(frozen=True)
class RepeatPreviewView:
    interval_weeks: int
    count: int
    occurrences: list[OccurrenceView]   # 예약 가능 범위(1년) 안의 회차만
    beyond_horizon: int                 # 범위 밖이라 빠진 회차 수
