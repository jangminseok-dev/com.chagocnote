from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateRevisitSettingsCommand:
    """보낸 칸만 바꾼다 — 쓰는 자리(목록·완료 시트·하루 마무리)에서 한 칸씩 바꾼다. 빠진 칸은 지금 값."""

    ctx: ShopContext
    changes: dict[str, Any]
