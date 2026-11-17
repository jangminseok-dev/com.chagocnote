from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class RepeatRequest:
    """반복 예약(⑭) — interval_weeks 주마다 count 번(첫 예약 포함). skip 은 빼는 회차 번호(1 부터)."""

    interval_weeks: int
    count: int
    skip: tuple[int, ...] = ()


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
    repeat: RepeatRequest | None = None


@dataclass(frozen=True)
class SeriesOccurrenceView:
    starts_at: datetime     # 매장 시간대
    warnings: list[str]     # 그 회차의 경고 — 미리 본 뒤 그 사이 예약이 생겼을 수 있어 다시 싣는다(P16)


@dataclass(frozen=True)
class RegisteredSeriesView:
    id: int
    interval_weeks: int
    occurrences: list[SeriesOccurrenceView]   # 실제로 잡은 회차(뺀 것·1년 밖은 없다)


@dataclass(frozen=True)
class RegisteredVisitsView:
    visits: list[VisitView]
    warnings: list[str]   # overlap · closed_day · outside_hours — 막지 않는 경고(반복이면 첫 회차의 것)
    series: RegisteredSeriesView | None = None   # ⑭ 반복으로 잡았을 때만
