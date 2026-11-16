from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ListGuardianLinksQuery:
    user_id: int


@dataclass(frozen=True)
class GuardianLinkView:
    link_id: int
    shop_name: str
    linked_at: datetime   # 매장 시간대
    role: str = "primary"  # primary(받은 알림장으로 이었다) · family(초대로 이었다, ⑫)
    family_count: int = 0  # 기본 연결이면 살아 있는 가족의 수, 가족이면 0
    family_max: int = 0    # 기본 연결이면 매장이 정한 가족 수, 가족이면 0
