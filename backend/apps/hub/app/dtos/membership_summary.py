from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MembershipSummary:
    """한 유저가 지금 속해 있는 매장 하나."""

    shop_id: int
    shop_name: str
    role: str
