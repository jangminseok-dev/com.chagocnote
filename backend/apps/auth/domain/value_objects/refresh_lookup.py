from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RefreshStatus(Enum):
    ACTIVE = "active"    # 유효하고 아직 쓰지 않았다
    USED = "used"        # 이미 새 토큰으로 바뀌었다 — 다시 오면 탈취 신호
    MISSING = "missing"  # 모르는 토큰이거나 만료·폐기되었다


@dataclass(frozen=True)
class RefreshLookup:
    status: RefreshStatus
    user_id: int | None
