from __future__ import annotations

from dataclasses import dataclass, field

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.build_send_bundle_dto import BundlePartView
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
    # ⑭ `이 예약만 / 이후 전부`(취소에만) — 빠지면 지금처럼 이 예약만
    scope: str = "this"
    family: bool = True
    skip_visit_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class TransitionedVisitsView:
    visits: list[VisitView]
    notice: list[BundlePartView] = field(default_factory=list)   # ⑭ 이후 전부 취소 뒤 보호자에게 보낼 글
