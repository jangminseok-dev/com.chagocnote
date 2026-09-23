from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class GetVisitQuery:
    ctx: ShopContext
    visit_id: int


@dataclass(frozen=True)
class PreviousVisitView:
    visit_id: int
    starts_at: datetime   # 매장 시간대


@dataclass(frozen=True)
class VisitDetailView:
    visit: VisitView
    group: list[VisitView]                 # 같은 묶음의 다른 방문(같은 보호자 + 같은 시작 시각)
    previous_visit: PreviousVisitView | None   # 그 아이(보호자만이면 보호자)의 지난 완료 방문
    no_show_count: int                     # 이 보호자의 노쇼 횟수
