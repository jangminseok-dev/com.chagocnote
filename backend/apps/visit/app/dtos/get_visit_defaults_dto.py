from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import MenuBriefView


@dataclass(frozen=True)
class GetVisitDefaultsQuery:
    ctx: ShopContext
    pet_id: int


@dataclass(frozen=True)
class VisitDefaultsView:
    """예약 ② 화면에 미리 채울 값 — 그 아이의 지난 완료 방문('지난번처럼'). 없으면 빈 메뉴와 매장 기본 소요."""

    source_visit_id: int | None
    duration_minutes: int
    menus: list[MenuBriefView]   # 보관한 메뉴는 뺀다
