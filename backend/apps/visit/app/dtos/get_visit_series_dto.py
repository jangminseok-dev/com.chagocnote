from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class GetVisitSeriesQuery:
    ctx: ShopContext
    series_id: int


@dataclass(frozen=True)
class VisitSeriesView:
    """반복 묶음의 예약 목록(⑭) — 방문 상세의 `4주마다 · 6번 중 3번째` 줄을 누르면 보인다."""

    id: int
    interval_weeks: int
    visits: list[VisitView]   # 상태와 상관없이 (시작 시각, ID) 순
