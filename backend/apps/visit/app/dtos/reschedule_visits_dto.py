from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.build_send_bundle_dto import BundlePartView
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class RescheduleVisitsCommand:
    """같은 보호자의 예약 여러 개(가족 묶음)를 한 시각으로 함께 옮긴다. 전부 되거나 전부 안 된다."""

    ctx: ShopContext
    visit_ids: tuple[int, ...]
    starts_at: datetime
    # ⑭ `이 예약만 / 이후 전부` — 빠지면 지금처럼 이 예약만
    scope: str = "this"                    # this · following
    family: bool = True                    # following 에서 거짓이면 요청한 방문의 아이만
    skip_visit_ids: tuple[int, ...] = ()   # 걸린 회차를 빼고 다시 보낼 때


@dataclass(frozen=True)
class RescheduledVisitsView:
    visits: list[VisitView]
    warnings: list[str]
    notice: list[BundlePartView] = field(default_factory=list)   # ⑭ 이후 전부 뒤 보호자에게 보낼 글
