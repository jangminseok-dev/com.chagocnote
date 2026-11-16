from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class SetReportSkipCommand:
    """하루 마무리의 [보내지 않음](⑬ 설계 3.6) — skip 이 False 면 되돌린다(방문 상세에서)."""

    ctx: ShopContext
    visit_id: int
    skip: bool
