from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class TransitionVisitsCommand:
    """같은 보호자의 방문 여러 개(가족 묶음)에 같은 행동 하나. 전부 되거나 전부 안 된다(V6).

    action: start · complete · cancel · no_show · revert. cancel_reason 은 cancel 일 때만, 반드시.
    """

    ctx: ShopContext
    visit_ids: tuple[int, ...]
    action: str
    cancel_reason: str | None


@dataclass(frozen=True)
class TransitionedVisitsView:
    visits: list[VisitView]
