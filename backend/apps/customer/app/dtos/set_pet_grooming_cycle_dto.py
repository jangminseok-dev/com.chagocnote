from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class SetPetGroomingCycleCommand:
    """그 아이의 미용 주기를 직접 정한다(⑬). weeks 가 None 이면 지운다 — 지난 방문에서 계산한 값으로 돌아간다."""

    ctx: ShopContext
    pet_id: int
    weeks: int | None
