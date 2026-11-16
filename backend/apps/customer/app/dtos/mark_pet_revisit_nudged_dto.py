from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class MarkPetRevisitNudgedCommand:
    """다시 올 때라고 안내했다(⑬) — 안내 미리 보기에서 공유 시트를 연 날을 오늘로 적는다."""

    ctx: ShopContext
    pet_id: int
