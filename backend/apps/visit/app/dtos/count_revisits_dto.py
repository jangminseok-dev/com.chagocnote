from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class CountRevisitsQuery:
    ctx: ShopContext


@dataclass(frozen=True)
class RevisitCountsView:
    soon: int
    due: int
