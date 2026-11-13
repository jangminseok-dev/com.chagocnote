from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.sales_repository import SalesVisitKind
from visit.app.services.pet_cards import PetCard
from visit.domain.services.sales_period import Span


@dataclass(frozen=True)
class ListSalesVisitsQuery:
    ctx: ShopContext
    span: Span
    anchor: date | None
    filter: SalesVisitKind
    menu_id: int | None      # filter 가 menu 일 때만 쓴다
    cursor: str | None


@dataclass(frozen=True)
class SalesVisitItemView:
    """매출 탭에서 누르면 나오는 방문 한 줄. 이름을 보일 수 없는 아이와 보호자만의 방문은 pet 이 None 이다 —
    방문은 그대로 보인다(금액을 채우러 갈 수 있어야 한다)."""

    visit_id: int
    date: date
    pet: PetCard | None
    amount: int | None


@dataclass(frozen=True)
class SalesVisitsView:
    items: list[SalesVisitItemView]
    next_cursor: str | None
